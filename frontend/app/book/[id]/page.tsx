"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getBook,
  listCharacters,
  streamChat,
  streamGroupChat,
  getConversationHistory,
  clearConversationHistory,
  getRelationships,
  type BookInfo,
  type CharacterInfo,
  type CharacterRelationship,
  type ChatMessage,
} from "@/lib/api";
import ChatBubble from "./components/ChatBubble";
import CharacterTabs from "./components/CharacterTabs";
import RelationshipGraph from "./components/RelationshipGraph";
import styles from "./page.module.css";

type DisplayMessage = ChatMessage & {
  character_id?: string;
  character_name?: string;
};

export default function BookPage() {
  const params = useParams();
  const bookId = params?.id as string;
  const [book, setBook] = useState<BookInfo | null>(null);
  const [characters, setCharacters] = useState<CharacterInfo[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingBook, setLoadingBook] = useState(true);
  const [groupMode, setGroupMode] = useState(false);
  const [showGraph, setShowGraph] = useState(false);
  const [relationships, setRelationships] = useState<CharacterRelationship[]>([]);
  const [hasMemory, setHasMemory] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!bookId) return;
    setLoadingBook(true);
    Promise.all([getBook(bookId), listCharacters(bookId), getRelationships(bookId)])
      .then(([b, chars, rels]) => {
        setBook(b);
        setCharacters(chars);
        setRelationships(rels);
        if (chars.length && !selectedId) setSelectedId(chars[0].id);
      })
      .catch(() => setError("Book not found"))
      .finally(() => setLoadingBook(false));
  }, [bookId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!bookId || !selectedId || groupMode) return;
    getConversationHistory(bookId, selectedId)
      .then((h) => {
        setHasMemory(!!h.memory_summary);
      })
      .catch(() => {});
  }, [bookId, selectedId, groupMode]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const selected = characters.find((c) => c.id === selectedId);

  const charIndexMap = useCallback(
    () => {
      const map: Record<string, number> = {};
      characters.forEach((c, i) => { map[c.id] = i; });
      return map;
    },
    [characters]
  );

  const handleClearMemory = useCallback(async () => {
    if (!bookId || !selectedId) return;
    try {
      await clearConversationHistory(bookId, selectedId);
      setHasMemory(false);
      setMessages([]);
    } catch {
      setError("Failed to clear memory");
    }
  }, [bookId, selectedId]);

  const sendSingle = useCallback(async () => {
    const text = input.trim();
    if (!text || !bookId || !selectedId || streaming) return;
    setInput("");
    const userMsg: DisplayMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setStreaming(true);
    setError(null);

    let fullContent = "";
    let citations: DisplayMessage["citations"] = [];
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
            citations: citations?.length ? citations : undefined,
          };
        }
        return next;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
      setMessages((prev) =>
        prev[prev.length - 1]?.role === "assistant" && !prev[prev.length - 1]?.content
          ? prev.slice(0, -1)
          : prev
      );
    } finally {
      setStreaming(false);
      inputRef.current?.focus();
    }
  }, [bookId, selectedId, input, messages, streaming]);

  const sendGroup = useCallback(async () => {
    const text = input.trim();
    if (!text || !bookId || !characters.length || streaming) return;
    setInput("");
    const userMsg: DisplayMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setStreaming(true);
    setError(null);

    const charIds = characters.map((c) => c.id);
    let currentCharId = "";
    let currentCharName = "";
    let currentContent = "";
    let citations: DisplayMessage["citations"] = [];

    try {
      for await (const event of streamGroupChat(bookId, charIds, text, messages.slice(-60))) {
        if (event.type === "character_start") {
          currentCharId = event.character_id ?? "";
          currentCharName = event.character_name ?? "";
          currentContent = "";
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: "",
              character_id: currentCharId,
              character_name: currentCharName,
            },
          ]);
        }
        if (event.type === "content" && event.content) {
          currentContent += event.content;
          const cc = currentContent;
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              next[next.length - 1] = { ...last, content: cc };
            }
            return next;
          });
        }
        if (event.type === "citations" && event.citations) {
          citations = event.citations;
        }
        if (event.type === "error") setError(event.content ?? "Stream error");
      }
      if (citations?.length) {
        setMessages((prev) => {
          const next = [...prev];
          const lastAssistantIdx = next.findLastIndex((m) => m.role === "assistant");
          if (lastAssistantIdx >= 0) {
            next[lastAssistantIdx] = { ...next[lastAssistantIdx], citations };
          }
          return next;
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Group chat failed");
    } finally {
      setStreaming(false);
      inputRef.current?.focus();
    }
  }, [bookId, characters, input, messages, streaming]);

  const send = groupMode ? sendGroup : sendSingle;

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    },
    [send]
  );

  const idxMap = charIndexMap();

  if (loadingBook) {
    return (
      <main className={styles.main}>
        <div className={styles.skeletonHeader}>
          <div className={styles.skeletonLine} style={{ width: "60%" }} />
          <div className={styles.skeletonLine} style={{ width: "40%" }} />
          <div className={styles.skeletonTabs}>
            {[1, 2, 3].map((i) => (
              <div key={i} className={styles.skeletonTab} />
            ))}
          </div>
        </div>
      </main>
    );
  }

  if (error && !book) {
    return (
      <main className={styles.main}>
        <p className={styles.error}>{error}</p>
        <Link href="/" className={styles.back}>
          &larr; Back
        </Link>
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <Link href="/" className={styles.back}>
          &larr; Books
        </Link>
        <h1 className={styles.title}>{book?.title ?? "\u2026"}</h1>

        <div className={styles.modeToggle}>
          <button
            type="button"
            className={`${styles.modeBtn} ${!groupMode && !showGraph ? styles.modeBtnActive : ""}`}
            onClick={() => { setGroupMode(false); setShowGraph(false); setMessages([]); }}
          >
            Single Character
          </button>
          <button
            type="button"
            className={`${styles.modeBtn} ${groupMode ? styles.modeBtnActive : ""}`}
            onClick={() => { setGroupMode(true); setShowGraph(false); setMessages([]); }}
          >
            Group Chat
          </button>
          {relationships.length > 0 && (
            <button
              type="button"
              className={`${styles.modeBtn} ${showGraph ? styles.modeBtnActive : ""}`}
              onClick={() => { setShowGraph(!showGraph); }}
            >
              Relationships
            </button>
          )}
        </div>

        {!groupMode && (
          <CharacterTabs
            characters={characters}
            selectedId={selectedId}
            onSelect={(id) => { setSelectedId(id); setMessages([]); }}
            groupMode={groupMode}
          />
        )}
      </header>

      {!groupMode && selected && (
        <div className={styles.charMeta}>
          <p className={styles.characterDesc}>
            {selected.description || `Chat as ${selected.name}.`}
          </p>
          <div className={styles.memoryRow}>
            {hasMemory && (
              <span className={styles.memoryBadge}>Remembers past chats</span>
            )}
            <button
              type="button"
              className={styles.clearBtn}
              onClick={handleClearMemory}
            >
              Clear memory
            </button>
          </div>
        </div>
      )}

      {groupMode && !showGraph && (
        <p className={styles.characterDesc}>
          All {characters.length} characters will respond to your messages in turn.
        </p>
      )}

      {showGraph && (
        <RelationshipGraph
          characters={characters}
          relationships={relationships}
        />
      )}

      {!showGraph && (
        <>
          <div className={styles.chat}>
            {messages.length === 0 && (
              <p className={styles.hint}>
                {groupMode
                  ? "Say something to all characters\u2026"
                  : `Say something to ${selected?.name ?? "the character"}\u2026`}
              </p>
            )}
            {messages.map((m, i) => (
              <ChatBubble
                key={i}
                role={m.role}
                content={m.content}
                citations={m.citations}
                characterName={m.character_name}
                characterColorIdx={m.character_id ? idxMap[m.character_id] : undefined}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className={styles.inputWrap}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={
                groupMode
                  ? "Message all characters\u2026"
                  : `Message ${selected?.name ?? "character"}\u2026`
              }
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
              {streaming ? "..." : "Send"}
            </button>
          </div>
        </>
      )}

      {error && <p className={styles.errorInline}>{error}</p>}
    </main>
  );
}
