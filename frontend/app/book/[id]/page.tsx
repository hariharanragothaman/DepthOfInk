"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getBook,
  listCharacters,
  streamChat,
  type BookInfo,
  type CharacterInfo,
  type ChatMessage,
} from "@/lib/api";
import styles from "./page.module.css";

type Citation = { text: string; page: number; score?: number };

export default function BookPage() {
  const params = useParams();
  const bookId = params?.id as string;
  const [book, setBook] = useState<BookInfo | null>(null);
  const [characters, setCharacters] = useState<CharacterInfo[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!bookId) return;
    getBook(bookId)
      .then(setBook)
      .catch(() => setError("Book not found"));
    listCharacters(bookId)
      .then((list) => {
        setCharacters(list);
        if (list.length && !selectedId) setSelectedId(list[0].id);
      })
      .catch(() => setError("Failed to load characters"));
  }, [bookId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const selected = characters.find((c) => c.id === selectedId);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || !bookId || !selectedId || streaming) return;
    setInput("");
    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setStreaming(true);
    setError(null);

    let fullContent = "";
    let citations: Citation[] = [];
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      for await (const event of streamChat(bookId, selectedId, text, messages)) {
        if (event.type === "content" && event.content) {
          fullContent += event.content;
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              next[next.length - 1] = { ...last, content: fullContent };
            }
            return next;
          });
        }
        if (event.type === "citations" && event.citations) citations = event.citations;
        if (event.type === "error") setError(event.content ?? "Stream error");
      }
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant") {
          next[next.length - 1] = {
            ...last,
            content: fullContent,
            citations: citations.length ? citations : undefined,
          };
        }
        return next;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
      setMessages((prev) => (prev[prev.length - 1]?.role === "assistant" && !prev[prev.length - 1]?.content ? prev.slice(0, -1) : prev));
    } finally {
      setStreaming(false);
      inputRef.current?.focus();
    }
  }, [bookId, selectedId, input, messages, streaming]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    },
    [send]
  );

  if (error && !book) {
    return (
      <main className={styles.main}>
        <p className={styles.error}>{error}</p>
        <Link href="/" className={styles.back}>← Back</Link>
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <Link href="/" className={styles.back}>← Books</Link>
        <h1 className={styles.title}>{book?.title ?? "…"}</h1>
        <div className={styles.characterTabs}>
          {characters.map((c) => (
            <button
              key={c.id}
              type="button"
              className={`${styles.tab} ${selectedId === c.id ? styles.tabActive : ""}`}
              onClick={() => setSelectedId(c.id)}
            >
              {c.name}
            </button>
          ))}
        </div>
      </header>

      {selected && (
        <p className={styles.characterDesc}>
          {selected.description || `Chat as ${selected.name}.`}
        </p>
      )}

      <div className={styles.chat}>
        {messages.length === 0 && (
          <p className={styles.hint}>Say something to {selected?.name ?? "the character"}…</p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={m.role === "user" ? styles.msgUser : styles.msgAssistant}
          >
            <div className={styles.msgContent}>{m.content}</div>
            {m.citations && m.citations.length > 0 && (
              <details className={styles.citations}>
                <summary>Cited from the book ({m.citations.length})</summary>
                <ul>
                  {m.citations.map((c, j) => (
                    <li key={j}>
                      <span className={styles.citePage}>Page {c.page}</span>
                      <span className={styles.citeText}>{c.text.slice(0, 200)}{c.text.length > 200 ? "…" : ""}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        ))}
        {streaming && (
          <div className={styles.msgAssistant}>
            <div className={styles.msgContent}>…</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className={styles.inputWrap}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={`Message ${selected?.name ?? "character"}…`}
          className={styles.input}
          rows={2}
          disabled={streaming}
        />
        <button
          type="button"
          onClick={send}
          disabled={!input.trim() || streaming}
          className={styles.sendBtn}
        >
          Send
        </button>
      </div>

      {error && <p className={styles.errorInline}>{error}</p>}
    </main>
  );
}
