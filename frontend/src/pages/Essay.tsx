import { ArrowLeft, Clock, ExternalLink, GraduationCap, Languages } from "lucide-react";
import { Link, useLocation, useParams } from "react-router-dom";

import { isNotFound } from "@/api/client";
import { useEssay, useEssays, useUniversityMap } from "@/api/hooks";
import type { EssaySummary } from "@/api/types";
import { Card, SectionTitle } from "@/components/ds/Card";
import { EmptyState, ErrorState, PageSkeleton } from "@/components/ds/states";
import { EssayCard, LevelBadge, readingMinutes } from "@/components/essays/EssayCard";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/misc";
import { t } from "@/i18n/ru";

/** Up to 3 other essays: same university first, then a shared major; bachelor essays before others. */
function similar(all: EssaySummary[], essay: EssaySummary): EssaySummary[] {
  const score = (e: EssaySummary) =>
    (essay.university_id && e.university_id === essay.university_id ? 4 : 0) +
    (e.majors.some((m) => essay.majors.includes(m)) ? 2 : 0) +
    (e.level === essay.level ? 1 : 0);
  return all
    .filter((e) => e.id !== essay.id && score(e) >= 2)
    .sort((a, b) => score(b) - score(a) || a.id.localeCompare(b.id))
    .slice(0, 3);
}

export function Essay() {
  const { id = "" } = useParams();
  const back = (useLocation().state as { back?: string } | null)?.back ?? "";
  const essay = useEssay(id);
  const essays = useEssays();
  const { map } = useUniversityMap();

  const backLink = (
    <Link to={`/essays${back}`} className="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline">
      <ArrowLeft className="h-4 w-4" /> {t.essays.back}
    </Link>
  );

  if (essay.isPending) return <PageSkeleton />;
  if (essay.isError && !essay.data)
    return (
      <div className="space-y-4">
        {backLink}
        {isNotFound(essay.error) ? (
          <EmptyState title={t.essays.notFound} />
        ) : (
          <ErrorState onRetry={() => essay.refetch()} />
        )}
      </div>
    );

  const e = essay.data!;
  const uni = e.university_id ? map.get(e.university_id) : undefined;
  const paragraphs = e.body.split(/\n\s*\n/).filter((p) => p.trim());
  const more = similar(essays.data ?? [], e);

  return (
    <div className="space-y-5">
      {backLink}

      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <LevelBadge level={e.level} />
          <span className="text-xs font-semibold text-muted-foreground">{t.essays.kinds[e.kind]}</span>
        </div>
        <h1 className="text-2xl font-bold leading-tight md:text-3xl">{e.school ?? t.essays.title}</h1>
        {(e.topics.length > 0 || e.program) && (
          <p className="text-muted-foreground">{e.topics.length ? e.topics.join(" · ") : e.program}</p>
        )}
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
          {e.author && (
            <span>
              {t.essays.author}: <span className="font-semibold text-foreground">{e.author}</span>
            </span>
          )}
          <span className="inline-flex items-center gap-1">
            <Clock className="h-4 w-4" aria-hidden /> {t.essays.minutes(readingMinutes(e.word_count))} ·{" "}
            {t.essays.words(e.word_count)}
          </span>
          <span className="inline-flex items-center gap-1">
            <Languages className="h-4 w-4" aria-hidden /> {t.essays.english}
          </span>
        </p>
      </header>

      <div className="grid gap-5 lg:grid-cols-[1fr_300px]">
        <Card className="min-w-0 p-5 md:p-8">
          {e.prompt && (
            <p className="mb-5 rounded-md bg-muted p-3 text-sm">
              <span className="font-semibold">{t.essays.prompt}:</span> <span lang="en">{e.prompt}</span>
            </p>
          )}
          <article lang="en" className="max-w-prose space-y-4 break-words text-[15px] leading-relaxed md:text-base">
            {paragraphs.map((p, i) => (
              <p key={i} className="whitespace-pre-line">
                {p.trim()}
              </p>
            ))}
          </article>
          {e.references.length > 0 && (
            <Collapsible className="mt-6 border-t pt-4">
              <CollapsibleTrigger className="text-sm font-semibold text-primary hover:underline">
                {t.essays.references} ({e.references.length})
              </CollapsibleTrigger>
              <CollapsibleContent>
                <ul lang="en" className="mt-3 space-y-2 break-words text-xs text-muted-foreground">
                  {e.references.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </CollapsibleContent>
            </Collapsible>
          )}
        </Card>

        <aside className="space-y-3">
          <Card className="space-y-3 p-4">
            <p className="text-sm font-bold">
              {e.license === "CC_BY_NC_SA_4_0" ? t.essays.licenseCc : t.essays.licenseUnknown}
            </p>
            <p className="text-xs text-muted-foreground">{t.essays.licenseNote}</p>
            <div className="flex flex-col gap-2">
              <Button variant="outline" size="sm" asChild>
                <a href={e.source_url} target="_blank" rel="noreferrer">
                  {t.essays.openSource} <ExternalLink />
                </a>
              </Button>
              {e.original_url && (
                <Button variant="ghost" size="sm" asChild>
                  <a href={e.original_url} target="_blank" rel="noreferrer">
                    {t.essays.openOriginal} <ExternalLink />
                  </a>
                </Button>
              )}
            </div>
          </Card>
          {uni && (
            <Card className="p-4">
              <p className="text-xs font-semibold text-muted-foreground">{t.essays.universityPage}</p>
              <Link
                to={`/university/${uni.id}`}
                className="mt-1 inline-flex items-center gap-2 font-semibold text-primary hover:underline"
              >
                <GraduationCap className="h-4 w-4" /> {uni.name}
              </Link>
            </Card>
          )}
        </aside>
      </div>

      {more.length > 0 && (
        <section>
          <SectionTitle>{t.essays.similar}</SectionTitle>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {more.map((m) => (
              <EssayCard key={m.id} essay={m} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
