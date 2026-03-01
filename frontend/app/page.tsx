"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { listBooks, uploadPdf, deleteBook, retryBook, type BookInfo } from "@/lib/api";
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

  const MAX_FILE_SIZE_MB = 50;

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setError("Please choose a PDF file.");
        return;
      }
      if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
        setError(`File too large. Maximum size is ${MAX_FILE_SIZE_MB} MB.`);
        return;
      }
      setUploading(true);
      setUploadStage("Uploading PDF...");
      setError(null);
      try {
        const book = await uploadPdf(file, undefined);
        setBooks((prev) => [book, ...prev]);
        setUploadStage("Redirecting...");
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

  const handleDelete = useCallback(
    async (e: React.MouseEvent, bookId: string) => {
      e.preventDefault();
      e.stopPropagation();
      if (!confirm("Delete this book and all its data?")) return;
      try {
        await deleteBook(bookId);
        setBooks((prev) => prev.filter((b) => b.id !== bookId));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Delete failed");
      }
    },
    []
  );

  const handleRetry = useCallback(
    async (e: React.MouseEvent, bookId: string) => {
      e.preventDefault();
      e.stopPropagation();
      try {
        const updated = await retryBook(bookId);
        setBooks((prev) => prev.map((b) => (b.id === bookId ? updated : b)));
        router.push(`/book/${bookId}`);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Retry failed");
      }
    },
    [router]
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
            <p className={styles.uploadText}>
              <span className={styles.desktopOnly}>Drop a PDF here or click to choose</span>
              <span className={styles.mobileOnly}>Tap to choose a PDF</span>
            </p>
            <p className={styles.uploadHint}>
              Storybooks and narrative PDFs work best.
              <br />
              <span className={styles.sizeHint}>Max {MAX_FILE_SIZE_MB} MB</span>
            </p>
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
              <li key={b.id} className={styles.bookItem}>
                <Link href={`/book/${b.id}`} className={styles.bookCard}>
                  <span className={styles.bookTitle}>{b.title}</span>
                  <span className={styles.bookMeta}>
                    {b.status === "processing" ? (
                      <span className={styles.processingBadge}>Processing...</span>
                    ) : b.status === "error" ? (
                      <span className={styles.errorBadge}>Error</span>
                    ) : (
                      `${b.character_ids.length} characters`
                    )}
                  </span>
                </Link>
                <div className={styles.bookActions}>
                  {b.status === "error" && (
                    <button
                      className={styles.retryBtn}
                      onClick={(e) => handleRetry(e, b.id)}
                      title="Retry processing"
                    >
                      ↻
                    </button>
                  )}
                  <button
                    className={styles.deleteBtn}
                    onClick={(e) => handleDelete(e, b.id)}
                    title="Delete book"
                  >
                    ✕
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer className={styles.footer}>
        <p>Chat with characters from any storybook PDF.</p>
      </footer>
    </main>
  );
}
