import { httpRequest } from "../../../shared/api/httpClient";

export type LlmProviderId =
  | "openai"
  | "openai_compatible"
  | "openrouter"
  | "ollama"
  | "llama_cpp"
  | "huggingface"
  | "anthropic"
  | "custom_http";

export type LlmProviderSettings = {
  enabled: boolean;
  api_base: string;
  model: string;
  has_api_key?: boolean;
  api_key?: string | null;
  organization?: string;
  project?: string;
  timeout_seconds: number;
  max_tokens: number;
  temperature: number;
  streaming: boolean;
  vision: boolean;
  embedding_model?: string;
  context_window: number;
  mode?: "external_server" | "managed_server";
  server_binary_path?: string;
  model_path?: string;
  host?: string;
  port?: number;
  gpu_layers?: number;
  threads?: number;
  batch_size?: number;
};

export type LlmTaskName =
  | "tutor_chat"
  | "story_generation"
  | "quiz_generation"
  | "grammar_explanation"
  | "correction"
  | "placement";

export type LlmProfile = {
  id: string;
  name: string;
  provider: LlmProviderId;
  api_base: string;
  model: string;
  enabled: boolean;
  has_api_key: boolean;
  api_key?: string | null;
  timeout_seconds: number;
  temperature: number;
  max_tokens: number;
  context_window: number;
  streaming: boolean;
  vision_support: boolean;
  privacy_mode: "local" | "cloud";
  llama_connection_mode: "external_server" | "managed_command" | "expert_parsed_settings";
  llama_command: string;
  llama_config: LlamaCppParsedConfig;
  created_at?: string;
  updated_at?: string;
};

export type LlmProfileInput = Omit<
  LlmProfile,
  "id" | "has_api_key" | "privacy_mode" | "created_at" | "updated_at"
> & { has_api_key?: boolean };

export type LlamaCppParsedConfig = {
  binary_path: string;
  model_path: string;
  host: string;
  port: number;
  api_base: string;
  context_window: number;
  gpu_layers: number;
  flash_attention: boolean;
  parallel_slots: number;
  threads: number;
  batch_size: number;
  extra_allowed_args: string[];
};

export type SettingsDoc = {
  ai: {
    active_provider: LlmProviderId;
    system_prompt: string;
    providers: Record<LlmProviderId, LlmProviderSettings>;
    task_defaults: Record<LlmTaskName, { provider: LlmProviderId | ""; model: string }>;
    profiles: LlmProfile[];
    default_profile_id: string;
    task_overrides: Partial<Record<LlmTaskName, string>>;
  };
};

export async function fetchAppSettings(): Promise<SettingsDoc> {
  return httpRequest<SettingsDoc>("/api/settings");
}

export async function updateAppSettings(payload: SettingsDoc): Promise<SettingsDoc> {
  return httpRequest<SettingsDoc>("/api/settings", { method: "PUT", body: payload });
}

export async function fetchLlmProfiles(): Promise<{
  profiles: LlmProfile[];
  default_profile_id: string;
}> {
  return httpRequest("/api/ai/llm/profiles");
}

export async function createLlmProfile(payload: LlmProfileInput): Promise<LlmProfile> {
  return httpRequest("/api/ai/llm/profiles", { method: "POST", body: payload });
}

export async function updateLlmProfile(
  profileId: string,
  payload: LlmProfileInput,
): Promise<LlmProfile> {
  return httpRequest(`/api/ai/llm/profiles/${encodeURIComponent(profileId)}`, {
    method: "PUT",
    body: payload,
  });
}

export async function deleteLlmProfile(profileId: string): Promise<void> {
  await httpRequest(`/api/ai/llm/profiles/${encodeURIComponent(profileId)}`, {
    method: "DELETE",
  });
}

export async function testLlmProfile(profileId: string): Promise<{
  ok: boolean;
  status: string;
  detail: string;
  provider: string;
  model_count?: number;
}> {
  return httpRequest(`/api/ai/llm/profiles/${encodeURIComponent(profileId)}/test`, {
    method: "POST",
  });
}

export async function fetchLlmProfileModels(
  profileId: string,
): Promise<{ provider: string; models: { id: string; name: string }[] }> {
  return httpRequest(`/api/ai/llm/profiles/${encodeURIComponent(profileId)}/models`);
}

export async function fetchLlmModels(provider: LlmProviderId): Promise<{
  provider: string;
  models: { id: string; name: string }[];
}> {
  return httpRequest(`/api/ai/llm/models?provider=${encodeURIComponent(provider)}`);
}

export async function updateLlmRouting(payload: {
  default_profile_id: string;
  task_overrides: Partial<Record<LlmTaskName, string>>;
}): Promise<typeof payload> {
  return httpRequest("/api/ai/llm/routing", { method: "PUT", body: payload });
}
