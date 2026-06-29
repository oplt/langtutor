import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";

import { ReadingPanel } from "../../../modules/reading/components/ReadingPanel";
import Header from "../components/Header";

export default function ReadingPage() {
  return (
    <>
      <Header />
      <Box sx={{ width: "100%", maxWidth: { sm: "100%", md: 1400 } }}>
        <Card variant="outlined">
          <CardContent>
            <ReadingPanel />
          </CardContent>
        </Card>
      </Box>
    </>
  );
}
