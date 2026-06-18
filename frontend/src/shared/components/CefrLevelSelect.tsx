import MenuItem from "@mui/material/MenuItem";
import TextField, { type TextFieldProps } from "@mui/material/TextField";

import { CEFR_LEVELS, type CefrLevel } from "../../modules/learning/api/learningPathApi";

type CefrLevelSelectProps = Omit<TextFieldProps, "select" | "value" | "onChange"> & {
  value: CefrLevel;
  onChange: (level: CefrLevel) => void;
};

export function CefrLevelSelect({
  value,
  onChange,
  label = "CEFR level",
  size = "small",
  sx,
  ...rest
}: CefrLevelSelectProps) {
  return (
    <TextField
      select
      size={size}
      label={label}
      value={value}
      onChange={(event) => onChange(event.target.value as CefrLevel)}
      sx={{ minWidth: 90, ...sx }}
      {...rest}
    >
      {CEFR_LEVELS.map((level) => (
        <MenuItem key={level} value={level}>
          {level}
        </MenuItem>
      ))}
    </TextField>
  );
}
