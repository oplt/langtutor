import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Header from "../components/Header";
import { TutorChatPanel } from "../../../modules/tutor/components/TutorChatPanel";

export default function CoachPage() {
  return (
    <>
      <Header />
      <Box sx={{ width: "100%", maxWidth: { sm: "100%", md: 1200 }, minHeight: "70vh" }}>
        <Card sx={{ height: "100%", boxShadow: "none", border: "none" }}>
          <CardContent sx={{ height: "100%", p: { xs: 2, md: 3 } }}>
            <TutorChatPanel />
          </CardContent>
        </Card>
      </Box>
    </>
  );
}
