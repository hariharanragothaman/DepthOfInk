import styles from "../page.module.css";

type Citation = { text: string; page: number; score?: number; chapter?: number; chapter_title?: string };

type Props = {
  role: string;
  content: string;
  citations?: Citation[];
  characterName?: string;
  characterColorIdx?: number;
};

const CHAR_COLORS = [
  "var(--ink-char-1)",
  "var(--ink-char-2)",
  "var(--ink-char-3)",
  "var(--ink-char-4)",
  "var(--ink-char-5)",
  "var(--ink-char-6)",
];

export default function ChatBubble({ role, content, citations, characterName, characterColorIdx }: Props) {
  const isUser = role === "user";
  const color = characterColorIdx !== undefined ? CHAR_COLORS[characterColorIdx % CHAR_COLORS.length] : undefined;

  return (
    <div className={isUser ? styles.msgUser : styles.msgAssistant}>
      {characterName && (
        <div className={styles.charLabel} style={color ? { color } : undefined}>
          {characterName}
        </div>
      )}
      <div className={styles.msgContent}>{content || "\u00A0"}</div>
      {citations && citations.length > 0 && (
        <details className={styles.citations}>
          <summary>Cited from the book ({citations.length})</summary>
          <ul>
            {citations.map((c, j) => (
              <li key={j}>
                <span className={styles.citePage}>
                  Page {c.page}
                  {c.chapter ? `, Chapter ${c.chapter}` : ""}
                </span>
                <span className={styles.citeText}>
                  {c.text.slice(0, 200)}{c.text.length > 200 ? "\u2026" : ""}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
