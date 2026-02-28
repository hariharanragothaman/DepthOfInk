"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { listBooks, uploadPdf, type BookInfo } from "@/lib/api";
import styles from "./page.module.css";

export default function HomePage() {
  const [books, setBooks] = useState<BookInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
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
      setError(null);
      try {
        const book = await uploadPdf(file, undefined);
        setBooks((prev) => [book, ...prev]);
        window.location.href = `/book/${book.id}`;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    []
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
          <p className={styles.uploadText}>Processing PDF and extracting characters…</p>
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
          <p className={styles.muted}>Loading…</p>
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
        <p>MVP — Phase 2: memory, better retrieval, scene mode.</p>
      </footer>
    </main>
  );
}
