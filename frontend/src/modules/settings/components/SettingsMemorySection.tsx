import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Typography from "@mui/material/Typography";

import { MemoryWorkbenchPanel } from "../../../modules/memory/components/MemoryWorkbenchPanel";

export function SettingsMemorySection() {
  return (
    <Accordion variant="outlined" disableGutters>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="subtitle2">Learner memory workbench</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <MemoryWorkbenchPanel />
      </AccordionDetails>
    </Accordion>
  );
}
