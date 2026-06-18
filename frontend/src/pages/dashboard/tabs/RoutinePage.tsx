import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Header from "../components/Header";
import { BookLessonPanel } from "../../../modules/book/components/BookLessonPanel";

export default function RoutinePage() {
  return (
    <>
      <Header />
      <Box sx={{ width: "100%", maxWidth: { sm: "100%", md: 1200 } }}>
        <Stack spacing={2}>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <Typography variant="h5">Study plan</Typography>
            <Chip size="small" label="Structured lessons" color="success" />
          </Stack>
          <Card variant="outlined">
            <CardContent>
              <BookLessonPanel />
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="subtitle1">Spaced retrieval</Typography>
                <Divider />
                <Typography variant="body2" color="text.secondary">
                  Work through lesson blocks in order: vocabulary, dialogue, pronunciation,
                  listening, then quiz. Progress is saved per page so you can resume where you left off.
                </Typography>
              </Stack>
            </CardContent>
          </Card>
        </Stack>
      </Box>
    </>
  );
}
