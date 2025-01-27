from __future__ import annotations

from typing import Any, List
from .enums import Units
from .FormattingOptions import CONVERSION_FACTORS, FormattingOptions
from .layer_info import LayerInfo
from .device_profile import DeviceProfile

"""
    Model statistics has been taken from torchinfo project https://github.com/TylerYep/torchinfo
"""

class ModelStatistics:
    """Class for storing results of the summary."""

    def __init__(
        self,
        summary_list: list[LayerInfo],
        input_size: Any,
        total_input_size: int,
        formatting: FormattingOptions,
        device_profiles : List[DeviceProfile]
    ) -> None:
        self.summary_list = summary_list
        self.input_size = input_size
        self.formatting = formatting
        self.total_input = total_input_size
        self.total_mult_adds = 0
        self.total_params, self.trainable_params = 0, 0
        self.total_param_bytes, self.total_output_bytes = 0, 0
        self.total_energy = 0
        self.device_profiles = device_profiles
        self.total_energies = self.summary_list[0].total_energy_contributions

        # TODO: Figure out why the below functions using max() are ever 0
        # (they should always be non-negative), and remove the call to max().
        # Investigation: https://github.com/TylerYep/torchinfo/pull/195
        for layer_info in summary_list:
            if layer_info.is_leaf_layer:
                self.total_mult_adds += layer_info.macs
                if layer_info.num_params > 0:
                    # x2 for gradients
                    self.total_output_bytes += layer_info.output_bytes * 2
                if layer_info.is_recursive:
                    continue
                self.total_params += max(layer_info.num_params, 0)
                self.total_param_bytes += layer_info.param_bytes
                self.trainable_params += max(layer_info.trainable_params, 0)
            else:
                if layer_info.is_recursive:
                    continue
                leftover_params = layer_info.leftover_params()
                leftover_trainable_params = layer_info.leftover_trainable_params()
                self.total_params += max(leftover_params, 0)
                self.trainable_params += max(leftover_trainable_params, 0)
        self.formatting.set_layer_name_width(summary_list)

    def __repr__(self) -> str:
        """Print results of the summary."""
        divider = "=" * self.formatting.get_total_width()
        total_params = ModelStatistics.format_output_num(
            self.total_params, self.formatting.params_units
        )
        trainable_params = ModelStatistics.format_output_num(
            self.trainable_params, self.formatting.params_units
        )
        non_trainable_params = ModelStatistics.format_output_num(
            self.total_params - self.trainable_params, self.formatting.params_units
        )

        all_layers = self.formatting.layers_to_str(self.summary_list, self.total_params)

        total_energy_strings = []
        for device_profile, total_energy in zip(self.device_profiles, self.total_energies):
            total_energy_strings.append(f"Total energy for device [{str(device_profile)}] : {total_energy} J/inf\n")

        summary_str = (
            f"{divider}\n"
            f"{self.formatting.header_row()}{divider}\n"
            f"{all_layers}{divider}\n"
        )
        summary_str += "".join(total_energy_strings)

        return summary_str

    @staticmethod
    def float_to_megabytes(num: int) -> float:
        """Converts a number (assume floats, 4 bytes each) to megabytes."""
        return num * 4 / 1e6

    @staticmethod
    def to_megabytes(num: int) -> float:
        """Converts bytes to megabytes."""
        return num / 1e6

    @staticmethod
    def to_readable(num: int, units: Units = Units.AUTO) -> tuple[Units, float]:
        """Converts a number to millions, billions, or trillions."""
        if units == Units.AUTO:
            if num >= 1e12:
                return Units.TERABYTES, num / 1e12
            if num >= 1e9:
                return Units.GIGABYTES, num / 1e9
            return Units.MEGABYTES, num / 1e6
        return units, num / CONVERSION_FACTORS[units]

    @staticmethod
    def format_output_num(num: int, units: Units) -> str:
        units_used, converted_num = ModelStatistics.to_readable(num, units)
        if converted_num.is_integer():
            converted_num = int(converted_num)
        units_display = "" if units_used == Units.NONE else f" ({units_used})"
        fmt = "d" if isinstance(converted_num, int) else ".2f"
        return f"{units_display}: {converted_num:,{fmt}}"
