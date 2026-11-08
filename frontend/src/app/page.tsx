"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  BackendInfo,
  Task,
  createTask,
  deleteTask,
  fetchBackendInfo,
  fetchTasks,
  toggleTask,
} from "@/lib/api";

type Filter = "all" | "active" | "done";

const FILTER_LABEL: Record<Filter, string> = {
  all: "Semua",
  active: "Aktif",
  done: "Selesai",
};

export default function Home() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [info, setInfo] = useState<BackendInfo | null>(null);
  const [title, setTitle] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [taskList, backendInfo] = await Promise.all([
          fetchTasks(),
          fetchBackendInfo(),
        ]);
        if (cancelled) return;
        setTasks(taskList);
        setInfo(backendInfo);
        setError(null);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Gagal memuat data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = title.trim();
    if (!value || pending) return;
    setPending(true);
    try {
      setError(null);
      const created = await createTask(value);
      setTasks((prev) => [created, ...prev]);
      setTitle("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal menambah task.");
    } finally {
      setPending(false);
    }
  };

  const onToggle = async (task: Task) => {
    try {
      setError(null);
      const updated = await toggleTask(task.id, !task.completed);
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengubah task.");
    }
  };

  const onDelete = async (task: Task) => {
    try {
      setError(null);
      await deleteTask(task.id);
      setTasks((prev) => prev.filter((t) => t.id !== task.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal menghapus task.");
    }
  };

  const visible = useMemo(() => {
    switch (filter) {
      case "active":
        return tasks.filter((t) => !t.completed);
      case "done":
        return tasks.filter((t) => t.completed);
      default:
        return tasks;
    }
  }, [tasks, filter]);

  const remaining = useMemo(
    () => tasks.filter((t) => !t.completed).length,
    [tasks]
  );

  const serving = info?.color === "green" ? "green" : "blue";

  return (
    <main className="flex-1 w-full max-w-3xl mx-auto px-4 sm:px-6 py-10 flex flex-col gap-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-emerald-400">
            DevSecOps · Blue-Green Deployment
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight text-slate-100">
            Task Manager
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            PBL — Praktikum DevSecOps. Next.js · FastAPI · PostgreSQL.
          </p>
        </div>

        <div
          className="shrink-0 rounded-xl border border-slate-700/80 bg-slate-900/70 px-4 py-2 text-right"
          title="Instance backend yang sedang melayani via Nginx"
        >
          <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
            Serving
          </p>
          <p className="mt-1 flex items-center gap-2 justify-end text-sm font-semibold text-slate-100">
            <span
              className={`inline-block h-2.5 w-2.5 rounded-full ${
                serving === "green" ? "bg-emerald-400" : "bg-sky-400"
              }`}
            />
            {info ? `${info.color.toUpperCase()} · ${info.version}` : "…"}
          </p>
        </div>
      </header>

      <form
        onSubmit={onSubmit}
        className="flex gap-2 rounded-2xl border border-slate-800 bg-slate-900/60 p-2 shadow-lg shadow-black/20"
      >
        <label htmlFor="title" className="sr-only">
          Judul task
        </label>
        <input
          id="title"
          name="title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={140}
          placeholder="Tulis task baru… (mis. Review pipeline Trivy)"
          autoComplete="off"
          className="flex-1 bg-transparent px-3 py-3 text-slate-100 placeholder:text-slate-500 outline-none rounded-xl focus:ring-2 focus:ring-emerald-500/60"
        />
        <button
          type="submit"
          disabled={pending || !title.trim()}
          className="rounded-xl bg-emerald-500 px-5 py-3 font-semibold text-emerald-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40 focus:ring-2 focus:ring-emerald-300 outline-none"
        >
          {pending ? "Menyimpan…" : "Tambah"}
        </button>
      </form>

      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300"
        >
          {error}
        </div>
      )}

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 shadow-lg shadow-black/20">
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <div className="flex gap-1" role="tablist" aria-label="Filter task">
            {(Object.keys(FILTER_LABEL) as Filter[]).map((key) => (
              <button
                key={key}
                role="tab"
                aria-selected={filter === key}
                onClick={() => setFilter(key)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition focus:ring-2 focus:ring-emerald-500/60 outline-none ${
                  filter === key
                    ? "bg-slate-800 text-emerald-300"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {FILTER_LABEL[key]}
              </button>
            ))}
          </div>
          <p className="text-xs font-mono text-slate-500">{remaining} tersisa</p>
        </div>

        {loading ? (
          <p className="px-4 py-10 text-center text-sm text-slate-500">
            Memuat task…
          </p>
        ) : visible.length === 0 ? (
          <p className="px-4 py-10 text-center text-sm text-slate-500">
            {tasks.length === 0
              ? "Belum ada task. Tambahkan yang pertama 👆"
              : "Tidak ada task untuk filter ini."}
          </p>
        ) : (
          <ul className="divide-y divide-slate-800">
            {visible.map((task) => (
              <li
                key={task.id}
                className="flex items-center gap-3 px-4 py-3 hover:bg-slate-800/40 transition"
              >
                <input
                  id={`task-${task.id}`}
                  type="checkbox"
                  checked={task.completed}
                  onChange={() => onToggle(task)}
                  aria-label={`Tandai "${task.title}" selesai`}
                  className="h-5 w-5 accent-emerald-500 cursor-pointer"
                />
                <label
                  htmlFor={`task-${task.id}`}
                  className={`flex-1 text-sm leading-6 cursor-pointer break-words ${
                    task.completed
                      ? "text-slate-500 line-through decoration-slate-600"
                      : "text-slate-100"
                  }`}
                >
                  {task.title}
                </label>
                <button
                  onClick={() => onDelete(task)}
                  aria-label={`Hapus "${task.title}"`}
                  className="rounded-lg p-2 text-slate-500 transition hover:bg-red-500/10 hover:text-red-400 focus:ring-2 focus:ring-red-400/60 outline-none"
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M3 6h18" />
                    <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer className="text-center text-[11px] font-mono text-slate-600">
        gitleaks · bandit · semgrep · pip-audit · npm audit · CodeQL · Trivy —
        security gate di setiap push
      </footer>
    </main>
  );
}
