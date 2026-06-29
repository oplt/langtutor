import { useMutation } from "@tanstack/react-query";

import { generateReading, saveReading, type ReadingGenerateRequest, type ReadingGenerateResponse } from "../api/readingApi";

export function useGenerateReadingMutation() {
  return useMutation({
    mutationFn: (payload: ReadingGenerateRequest) => generateReading(payload),
  });
}

export function useSaveReadingMutation() {
  return useMutation({
    mutationFn: (reading: ReadingGenerateResponse) => saveReading(reading),
  });
}
