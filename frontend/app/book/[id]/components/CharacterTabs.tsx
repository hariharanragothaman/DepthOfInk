import type { CharacterInfo } from "@/lib/api";
import styles from "../page.module.css";

type Props = {
  characters: CharacterInfo[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  groupMode: boolean;
};

export default function CharacterTabs({ characters, selectedId, onSelect, groupMode }: Props) {
  return (
    <div className={styles.characterTabs}>
      {characters.map((c) => (
        <button
          key={c.id}
          type="button"
          className={`${styles.tab} ${!groupMode && selectedId === c.id ? styles.tabActive : ""}`}
          onClick={() => onSelect(c.id)}
        >
          {c.name}
        </button>
      ))}
    </div>
  );
}
