import { useMemo } from "react";
import type { CharacterInfo, CharacterRelationship } from "@/lib/api";
import styles from "../page.module.css";

type Props = {
  characters: CharacterInfo[];
  relationships: CharacterRelationship[];
};

const CHAR_COLORS = [
  "var(--ink-char-1)",
  "var(--ink-char-2)",
  "var(--ink-char-3)",
  "var(--ink-char-4)",
  "var(--ink-char-5)",
  "var(--ink-char-6)",
];

export default function RelationshipGraph({ characters, relationships }: Props) {
  const nodes = useMemo(() => {
    const count = characters.length;
    const cx = 300;
    const cy = 220;
    const rx = 240;
    const ry = 170;
    return characters.map((c, i) => {
      const angle = (2 * Math.PI * i) / count - Math.PI / 2;
      return {
        id: c.id,
        name: c.name,
        x: cx + rx * Math.cos(angle),
        y: cy + ry * Math.sin(angle),
        color: CHAR_COLORS[i % CHAR_COLORS.length],
      };
    });
  }, [characters]);

  const nodeMap = useMemo(() => {
    const m: Record<string, (typeof nodes)[0]> = {};
    for (const n of nodes) m[n.id] = n;
    return m;
  }, [nodes]);

  if (relationships.length === 0) {
    return (
      <div className={styles.graphEmpty}>
        <p>No character relationships detected.</p>
      </div>
    );
  }

  return (
    <div className={styles.graphContainer}>
      <svg
        viewBox="0 0 600 440"
        className={styles.graphSvg}
        xmlns="http://www.w3.org/2000/svg"
      >
        {relationships.map((rel, i) => {
          const src = nodeMap[rel.source_id];
          const tgt = nodeMap[rel.target_id];
          if (!src || !tgt) return null;
          const mx = (src.x + tgt.x) / 2;
          const my = (src.y + tgt.y) / 2;
          return (
            <g key={i}>
              <line
                x1={src.x}
                y1={src.y}
                x2={tgt.x}
                y2={tgt.y}
                stroke="var(--ink-border)"
                strokeWidth={1.5}
                opacity={0.6}
              />
              <text
                x={mx}
                y={my - 6}
                textAnchor="middle"
                fill="var(--ink-muted)"
                fontSize={10}
                fontFamily="var(--font-sans)"
              >
                {rel.relationship}
              </text>
            </g>
          );
        })}
        {nodes.map((node) => (
          <g key={node.id}>
            <circle
              cx={node.x}
              cy={node.y}
              r={24}
              fill="var(--ink-surface)"
              stroke={node.color}
              strokeWidth={2}
            />
            <text
              x={node.x}
              y={node.y + 38}
              textAnchor="middle"
              fill="var(--ink-text)"
              fontSize={11}
              fontWeight={500}
              fontFamily="var(--font-sans)"
            >
              {node.name}
            </text>
            <text
              x={node.x}
              y={node.y + 4}
              textAnchor="middle"
              fill={node.color}
              fontSize={12}
              fontWeight={600}
              fontFamily="var(--font-serif)"
            >
              {node.name.charAt(0)}
            </text>
          </g>
        ))}
      </svg>

      <div className={styles.graphLegend}>
        <h4 className={styles.graphLegendTitle}>Relationships</h4>
        <ul className={styles.graphLegendList}>
          {relationships.map((rel, i) => (
            <li key={i}>
              <strong>{rel.source_name}</strong>
              <span className={styles.graphRelLabel}>{rel.relationship}</span>
              <strong>{rel.target_name}</strong>
              {rel.description && (
                <span className={styles.graphRelDesc}> &mdash; {rel.description}</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
