import { Suspense, lazy, useState } from "react";
import Header from "../components/Header";
import Box from "@mui/material/Box";
import { PageLoading } from "../../../shared/components/PageLoading";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

const WordBankPanel = lazy(() =>
  import("../../../modules/notebook/components/WordBankPanel").then((module) => ({
    default: module.WordBankPanel,
  })),
);
const QuizPracticePanel = lazy(() =>
  import("../../../modules/learning/components/QuizPracticePanel").then((module) => ({
    default: module.QuizPracticePanel,
  })),
);
const MasteryPathPanel = lazy(() =>
  import("../../../modules/learning/components/MasteryPathPanel").then((module) => ({
    default: module.MasteryPathPanel,
  })),
);

const TASK_PANELS = [
  { id: "word-bank", label: "Word bank", Panel: WordBankPanel },
  { id: "quiz", label: "Quiz practice", Panel: QuizPracticePanel },
  { id: "mastery", label: "Mastery path", Panel: MasteryPathPanel },
] as const;

function PanelFallback() {
  return <PageLoading label="Loading panel…" />;
}

export default function TasksPage() {
  const [tab, setTab] = useState(0);
  const ActivePanel = TASK_PANELS[tab]?.Panel ?? WordBankPanel;

  return (
    <>
      <Header />
      <Box sx={{ width: "100%", maxWidth: { sm: "100%", md: 1200 } }}>
        <Tabs
          value={tab}
          onChange={(_event, value: number) => setTab(value)}
          sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}
        >
          {TASK_PANELS.map((panel) => (
            <Tab key={panel.id} label={panel.label} />
          ))}
        </Tabs>
        <Suspense fallback={<PanelFallback />}>
          <ActivePanel />
        </Suspense>
      </Box>
    </>
  );
}
