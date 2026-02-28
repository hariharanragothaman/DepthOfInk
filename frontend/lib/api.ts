const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type BookInfo = {
  id: string;
  title: string;
  character_ids: string[];
};

export type CharacterInfo = {
  id: string;
  name: string;
  description: string | null;
  example_quotes: string[];
};

export type ChatMessage = {
  role: string;
  content: string;
  citations?: { text: string; page: number; score?: number }[];
};

export async function listBooks(): Promise<BookInfo[]> {
  const r = await fetch(`${API_BASE}/books`);
  if (!r.ok) throw new Error("Failed to list books");
  return r.json();
}

export async function getBook(bookId: string): Promise<BookInfo> {
  const r = await fetch(`${API_BASE}/books/${bookId}`);
  if (!r.ok) throw new Error("Failed to get book");
  return r.json();
}

export async function uploadPdf(file: File, title?: string): Promise<BookInfo> {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  const r = await fetch(`${API_BASE}/books/upload?title=${title ?? ""}`, {
    method: "POST",
    body: form,
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  return r.json();
}

export async function listCharacters(bookId: string): Promise<CharacterInfo[]> {
  const r = await fetch(`${API_BASE}/books/${bookId}/characters`);
  if (!r.ok) throw new Error("Failed to list characters");
  return r.json();
}

export async function sendMessage(
  bookId: string,
  characterId: string,
  message: string,
  history: ChatMessage[]
): Promise<{ content: string; citations: { text: string; page: number }[] }> {
  const r = await fetch(`${API_BASE}/chat/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      book_id: bookId,
      character_id: characterId,
      message,
      history: history.map((m) => ({
        role: m.role,
        content: m.content,
        citations: m.citations ?? [],
      })),
    }),
  });
  if (!r.ok) throw new Error("Chat failed");
  return r.json();
}

export async function* streamChat(
  bookId: string,
  characterId: string,
  message: string,
  history: ChatMessage[]
): AsyncGenerator<{ type: string; content?: string; citations?: { text: string; page: number }[] }> {
  const r = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      book_id: bookId,
      character_id: characterId,
      message,
      history: history.map((m) => ({
        role: m.role,
        content: m.content,
        citations: m.citations ?? [],
      })),
    }),
  });
  if (!r.ok) throw new Error("Stream failed");
  const reader = r.body?.getReader();
  if (!reader) throw new Error("No body");
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        yield JSON.parse(line);
      } catch {
        // skip malformed
      }
    }
  }
  if (buf.trim()) {
    try {
      yield JSON.parse(buf);
    } catch {
      // skip
    }
  }
}
