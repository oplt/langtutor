import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Header from "../components/Header";
import { DocumentsPanel } from "../../../modules/documents/components/DocumentsPanel";

export default function DocumentsPage() {
  return (
    <>
      <Header />
      <Box sx={{ width: "100%", maxWidth: { sm: "100%", md: 1200 } }}>
        <Card variant="outlined">
          <CardContent>
            <DocumentsPanel />
          </CardContent>
        </Card>
      </Box>
    </>
  );
}
