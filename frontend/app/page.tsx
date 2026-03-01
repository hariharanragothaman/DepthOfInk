"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { listBooks, uploadPdf, type BookInfo } from "@/lib/api";
import styles from "./page.module.css";

export default function HomePage() {
  const router = useRouter();
  const [books, setBooks] = useState<BookInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadStage, setUploadStage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listBooks();
      setBooks(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load books");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setError("Please choose a PDF file.");
        return;
      }
      setUploading(true);
      setUploadStage("Uploading PDF...");
      setError(null);
      try {
        setUploadStage("Extracting text and characters...");
        const book = await uploadPdf(file, undefined);
        setBooks((prev) => [book, ...prev]);
        setUploadStage("Done! Redirecting...");
        router.push(`/book/${book.id}`);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setUploading(false);
        setUploadStage("");
      }
    },
    [router]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDrag(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );
  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDrag(true);
  }, []);
  const onDragLeave = useCallback(() => setDrag(false), []);
  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <h1 className={styles.title}>DepthOfInk</h1>
        <p className={styles.subtitle}>Upload a storybook PDF and talk to its characters.</p>
      </header>

      <section
        className={`${styles.upload} ${drag ? styles.uploadDrag : ""} ${uploading ? styles.uploadBusy : ""}`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
      >
        <input
          type="file"
          accept=".pdf"
          onChange={onInputChange}
          disabled={uploading}
          className={styles.fileInput}
          aria-label="Upload PDF"
        />
        {uploading ? (
          <>
            <div className={styles.spinner} />
            <p className={styles.uploadText}>{uploadStage}</p>
          </>
        ) : (
          <>
            <p className={styles.uploadText}>Drop a PDF here or click to choose</p>
            <p className={styles.uploadHint}>Storybooks and narrative PDFs work best.</p>
          </>
        )}
      </section>

      {error && <p className={styles.error}>{error}</p>}

      <section className={styles.books}>
        <h2 className={styles.booksTitle}>Your books</h2>
        {loading ? (
          <div className={styles.skeletonList}>
            {[1, 2, 3].map((i) => (
              <div key={i} className={styles.skeletonCard} />
            ))}
          </div>
        ) : books.length === 0 ? (
          <p className={styles.muted}>No books yet. Upload a PDF to get started.</p>
        ) : (
          <ul className={styles.bookList}>
            {books.map((b) => (
              <li key={b.id}>
                <Link href={`/book/${b.id}`} className={styles.bookCard}>
                  <span className={styles.bookTitle}>{b.title}</span>
                  <span className={styles.bookMeta}>{b.character_ids.length} characters</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer className={styles.footer}>
        <p>Phase 2 — memory, reranking, group chat, chapter-aware retrieval.</p>
      </footer>
    </main>
  );
}
