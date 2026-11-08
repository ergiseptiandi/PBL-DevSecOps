export type Task = {
  id: number;
  title: string;
  completed: boolean;
  created_at: string;
};

export type BackendInfo = {
  app: string;
  version: string;
  color: "blue" | "green";
};

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request gagal (HTTP ${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // biarkan detail default
    }
    throw new Error(detail);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export async function fetchTasks(): Promise<Task[]> {
  return handle(await fetch("/api/tasks", { cache: "no-store" }));
}

export async function createTask(title: string): Promise<Task> {
  return handle(
    await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    })
  );
}

export async function toggleTask(id: number, completed: boolean): Promise<Task> {
  return handle(
    await fetch(`/api/tasks/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ completed }),
    })
  );
}

export async function deleteTask(id: number): Promise<void> {
  return handle(await fetch(`/api/tasks/${id}`, { method: "DELETE" }));
}

export async function fetchBackendInfo(): Promise<BackendInfo> {
  return handle(await fetch("/api/version", { cache: "no-store" }));
}
