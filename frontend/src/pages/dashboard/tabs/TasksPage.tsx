import { Suspense, lazy, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
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

type TaskTabId = (typeof TASK_PANELS)[number]["id"];

function tabIndexFromParam(tab: string | null): number {
  const index = TASK_PANELS.findIndex((panel) => panel.id === tab);
  return index >= 0 ? index : 0;
}

function PanelFallback() {
  return <PageLoading label="Loading panel…" />;
}

export default function TasksPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = tabIndexFromParam(searchParams.get("tab"));

  const setTab = useCallback(
    (index: number) => {
      const nextTab: TaskTabId = TASK_PANELS[index]?.id ?? "word-bank";
      setSearchParams({ tab: nextTab }, { replace: true });
    },
    [setSearchParams],
  );

  return (
    <>
      <Header />
      <Box sx={{ width: "100%", maxWidth: { sm: "100%", md: 1200 } }}>
        <Tabs
          value={tab}
          onChange={(_event, value: number) => setTab(value)}
          aria-label="Practice tasks"
          sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}
        >
          {TASK_PANELS.map((panel, index) => (
            <Tab
              key={panel.id}
              id={`tasks-tab-${panel.id}`}
              aria-controls={`tasks-panel-${panel.id}`}
              label={panel.label}
              value={index}
            />
          ))}
        </Tabs>
        {TASK_PANELS.map((panel, index) => {
          const Panel = panel.Panel;
          return (
            <Box
              key={panel.id}
              id={`tasks-panel-${panel.id}`}
              role="tabpanel"
              aria-labelledby={`tasks-tab-${panel.id}`}
              hidden={tab !== index}
            >
              <Suspense fallback={<PanelFallback />}>
                <Panel />
              </Suspense>
            </Box>
          );
        })}
      </Box>
    </>
  );
}
