import type { CefrLevel } from "../../modules/learning/api/learningPathApi";

export const queryKeys = {
  learning: {
    levels: ["learning", "levels"] as const,
    progressSummary: ["learning", "progress", "summary"] as const,
    pathMap: (level: CefrLevel) => ["learning", "path", level, "map"] as const,
    pathDrill: (level: CefrLevel) => ["learning", "path", level, "drill"] as const,
  },
  notebook: {
    entries: ["notebook", "entries"] as const,
  },
  memory: {
    overview: ["memory", "overview"] as const,
    l3: ["memory", "l3"] as const,
  },
  book: {
    levels: ["book", "levels"] as const,
    detail: (level: CefrLevel) => ["book", level] as const,
    progress: (level?: CefrLevel) => ["book", "progress", level ?? "all"] as const,
    page: (level: CefrLevel, pageId: string) => ["book", level, "page", pageId] as const,
  },
  privacy: {
    preferences: ["privacy", "preferences"] as const,
    auditLog: (limit: number) => ["privacy", "audit-log", limit] as const,
  },
} as const;
