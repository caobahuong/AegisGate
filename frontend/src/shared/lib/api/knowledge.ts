import { KnowledgeChunkResponse } from "@/types";
import { apiClient } from "./client";

export async function fetchKnowledgeChunks(targetId?: string): Promise<KnowledgeChunkResponse[]> {
  return apiClient<KnowledgeChunkResponse[]>("/knowledge", {
    params: targetId ? { target_id: targetId } : undefined,
  });
}

export async function fetchKnowledgeChunkDetail(chunkId: string): Promise<KnowledgeChunkResponse> {
  return apiClient<KnowledgeChunkResponse>(`/knowledge/${encodeURIComponent(chunkId)}`);
}

export async function updateKnowledgeDocs(
  chunkId: string,
  docContent?: string,
  skillsContent?: string
): Promise<{ success: boolean }> {
  return apiClient<{ success: boolean }>(`/knowledge/${encodeURIComponent(chunkId)}/docs`, {
    method: "PUT",
    body: JSON.stringify({ doc_content: docContent, skills_content: skillsContent }),
  });
}
