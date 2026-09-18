import { ArrowRight, ArrowUp, Check, Loader2, RotateCcw, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";

import { useClearMentor, useMentor, useMentorAction, useSendMentor } from "@/api/hooks";
import type { MentorAction, MentorMessage } from "@/api/types";
import { PageHeader } from "@/components/ds/Card";
import { ErrorState } from "@/components/ds/states";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { cn } from "@/lib/utils";
import { useNetwork } from "@/store/ui";

const MAX_CHARS = 1000;

const STATUS_STYLE: Record<MentorAction["status"], string> = {
  pending: "bg-muted text-muted-foreground",
  applied: "bg-plus-soft text-plus",
  dismissed: "bg-muted text-muted-foreground",
  failed: "bg-blocker-soft text-blocker",
};

function ActionCard({ message, action, index }: { message: MentorMessage; action: MentorAction; index: number }) {
  const act = useMentorAction();
  const offline = useNetwork((s) => s.offline);
  const busy = act.isPending;
  const run = (apply: boolean) => act.mutate({ messageId: message.id, index, apply });
  const pending = (action.status ?? "pending") === "pending";

  return (
    <li className="rounded-xl border bg-card p-3">
      <p className="text-sm font-semibold leading-snug">{action.summary}</p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {pending ? (
          <>
            <Button size="sm" onClick={() => run(true)} disabled={busy || offline}>
              {busy && act.variables?.apply ? <Loader2 className="animate-spin" /> : <Check />} {t.mentor.apply}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => run(false)} disabled={busy || offline}>
              <X /> {t.mentor.dismiss}
            </Button>
          </>
        ) : (
          <>
            <span className={cn("rounded-md px-2 py-0.5 text-xs font-semibold", STATUS_STYLE[action.status ?? "pending"])}>
              {t.mentor.status[action.status ?? "pending"]}
            </span>
            {action.status === "applied" && (
              <Link to="/roadmap" className="inline-flex items-center gap-1 text-xs font-bold text-primary hover:underline">
                {t.mentor.openPlan} <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            )}
          </>
        )}
      </div>
    </li>
  );
}

function Bubble({ message }: { message: MentorMessage }) {
  if (message.role === "user") {
    return (
      <li className="flex justify-end">
        <p className="max-w-[85%] whitespace-pre-line rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-primary-foreground">
          {message.text}
        </p>
      </li>
    );
  }
  const actions = message.actions ?? [];
  return (
    <li className="flex gap-3">
      <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-hero-dark text-hero-dark-foreground">
        <Sparkles className="h-4 w-4" />
      </span>
      <div className="min-w-0 max-w-[85%] space-y-2">
        <p className="whitespace-pre-line rounded-2xl rounded-tl-md border bg-card px-4 py-2.5 leading-relaxed">{message.text}</p>
        {!message.generated && <p className="text-xs text-muted-foreground">{t.mentor.unavailable}</p>}
        {actions.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{t.mentor.proposals}</p>
            <ul className="space-y-2">
              {actions.map((a, i) => (
                <ActionCard key={i} message={message} action={a} index={i} />
              ))}
            </ul>
          </div>
        )}
      </div>
    </li>
  );
}

export function Mentor() {
  const messages = useMentor();
  const send = useSendMentor();
  const clear = useClearMentor();
  const offline = useNetwork((s) => s.offline);
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const list = messages.data ?? [];

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [list.length, send.isPending]);

  // grow the input with its content, up to ~5 lines
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }, [text]);

  const submit = (value = text) => {
    const v = value.trim();
    if (!v || send.isPending || offline || v.length > MAX_CHARS) return;
    send.mutate(v);
    setText("");
  };
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col">
      <PageHeader
        title={t.mentor.title}
        subtitle={t.mentor.subtitle}
        actions={
          list.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => clear.mutate()} disabled={clear.isPending || offline}>
              <RotateCcw /> {t.mentor.newChat}
            </Button>
          )
        }
      />

      {messages.isPending ? (
        <div className="space-y-3">
          <Skeleton className="ml-auto h-12 w-2/3 rounded-2xl" />
          <Skeleton className="h-24 w-3/4 rounded-2xl" />
        </div>
      ) : messages.isError && !messages.data ? (
        <ErrorState onRetry={() => messages.refetch()} />
      ) : list.length === 0 && !send.isPending ? (
        <section className="rounded-2xl border bg-card p-5 md:p-6">
          <h2 className="flex items-center gap-2 text-lg font-bold">
            <Sparkles className="h-5 w-5 text-primary" /> {t.mentor.emptyTitle}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">{t.mentor.emptyText}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {t.mentor.starters.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => submit(q)}
                disabled={offline}
                className="rounded-full border bg-background px-4 py-2 text-left text-sm font-semibold hover:border-primary hover:text-primary disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        </section>
      ) : (
        <ol className="space-y-5 pb-4" aria-live="polite">
          {list.map((m) => (
            <Bubble key={m.id} message={m} />
          ))}
          {send.isPending && (
            <li className="flex items-center gap-3 text-sm text-muted-foreground">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-hero-dark text-hero-dark-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
              </span>
              {t.mentor.thinking}
            </li>
          )}
        </ol>
      )}
      <div ref={endRef} />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="sticky bottom-16 z-20 mt-4 rounded-2xl border bg-card/95 p-2 shadow-lg backdrop-blur md:bottom-4"
      >
        <div className="flex items-end gap-2">
          <label htmlFor="mentor-input" className="sr-only">
            {t.mentor.placeholder}
          </label>
          <textarea
            id="mentor-input"
            ref={inputRef}
            rows={1}
            value={text}
            maxLength={MAX_CHARS}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKey}
            placeholder={t.mentor.placeholder}
            disabled={offline}
            className="max-h-36 min-h-11 flex-1 resize-none bg-transparent px-3 py-2.5 outline-none placeholder:text-muted-foreground"
          />
          <Button
            type="submit"
            size="icon"
            className="h-11 w-11 shrink-0 rounded-xl"
            disabled={!text.trim() || send.isPending || offline}
            aria-label={t.mentor.send}
          >
            {send.isPending ? <Loader2 className="animate-spin" /> : <ArrowUp />}
          </Button>
        </div>
        <p className="flex justify-between gap-2 px-3 pb-1 pt-1 text-[11px] text-muted-foreground">
          <span>{t.mentor.disclaimer}</span>
          {text.length > MAX_CHARS - 200 && <span>{text.length}/{MAX_CHARS}</span>}
        </p>
      </form>
    </div>
  );
}
