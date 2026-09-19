import { ArrowLeft, BookOpen, CalendarClock, Globe2, Loader2, Plus, ExternalLink, FileText, Info, Star } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useCountryPreview, useEssays, useExplain, useFavorites, useSaveProfile, useProfile, useRecommendations, useToggleFavorite, useUniversities } from "@/api/hooks";
import type { Profile, University as Uni } from "@/api/types";
import { ChanceBadge, GeneratedMark, ReasonChip, SourceBadge, TierBadge } from "@/components/ds/badges";
import { Card, SectionTitle } from "@/components/ds/Card";
import { EmptyState, ErrorState, PageSkeleton } from "@/components/ds/states";
import { DOCUMENT_TITLES } from "@/components/ds/documents";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { academicGpa4, academicLabel } from "@/lib/academic";
import { profileToIn } from "@/lib/profileIn";
import { countryName, money, oneIn, projectDeadline, rank, shortDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useNetwork } from "@/store/ui";

type Sourced = { value?: unknown; source_url?: string | null; checked_at?: string | null; is_demo: boolean };

function best(profile: Profile, type: string): number | null {
  const s = profile.achievements.filter((a) => a.type === type && a.status === "done" && a.score != null).map((a) => a.score as number);
  return s.length ? Math.max(...s) : null;
}

function Row({ label, value, yours, ok, fact }: { label: string; value: ReactNode; yours?: ReactNode; ok?: boolean | null; fact: Sourced }) {
  const missing = fact.value == null;
  return (
    <tr className="border-t align-top">
      <th scope="row" className="py-3 pr-3 text-left text-xs font-semibold text-muted-foreground">
        {label}
      </th>
      <td className="py-3 pr-3 text-sm">
        <div className={cn("font-semibold", missing && "font-normal italic text-muted-foreground")}>{missing ? t.common.notPublished : value}</div>
        <SourceBadge sourceUrl={fact.source_url} checkedAt={fact.checked_at} isDemo={fact.is_demo} className="mt-1" />
      </td>
      <td className={cn("py-3 text-sm font-semibold", ok === true && "text-plus", ok === false && "text-risk")}>{yours ?? "—"}</td>
    </tr>
  );
}

function Requirements({ uni, profile }: { uni: Uni; profile: Profile }) {
  const sat = best(profile, "SAT");
  const ielts = best(profile, "IELTS");
  const toefl = best(profile, "TOEFL");
  const gpa4 = academicGpa4(profile);
  const satRange = uni.sat.value;
  const cost = uni.cost_per_year_usd.value;
  return (
    <div className="-mx-1 overflow-x-auto px-1">
      <table className="w-full min-w-[300px]">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
            <th className="pb-2 font-semibold" />
            <th className="pb-2 pr-3 font-semibold">{t.university.requirement}</th>
            <th className="pb-2 font-semibold">{t.university.yours}</th>
          </tr>
        </thead>
        <tbody>
          <Row label={t.university.acceptance} value={oneIn(uni.acceptance_rate.value)} fact={uni.acceptance_rate} />
          <Row
            label={t.university.sat}
            value={satRange ? `${satRange.p25}–${satRange.p75}` : null}
            fact={uni.sat}
            yours={sat ?? "не сдан"}
            ok={satRange && sat != null ? sat >= satRange.p25 : null}
          />
          <Row
            label={t.university.gpa}
            value={uni.gpa_avg.value?.toFixed(2)}
            fact={uni.gpa_avg}
            yours={<span title={t.common.approxGpa}>{gpa4 !== null ? "≈" : ""}{(gpa4 === null ? academicLabel(profile) + " · без перевода" : gpa4.toFixed(1))}</span>}
            ok={uni.gpa_avg.value != null && gpa4 !== null ? gpa4 >= uni.gpa_avg.value - 0.2 : null}
          />
          <Row
            label={t.university.ielts}
            value={uni.ielts_min.value}
            fact={uni.ielts_min}
            yours={ielts ?? (toefl != null ? `TOEFL ${toefl}` : "нет")}
            ok={uni.ielts_min.value != null && ielts != null ? ielts >= uni.ielts_min.value : null}
          />
          <Row
            label={t.university.cost}
            value={money(cost)}
            fact={uni.cost_per_year_usd}
            yours={money(profile.budget_per_year_usd)}
            ok={cost != null ? cost <= profile.budget_per_year_usd : null}
          />
          <Row
            label={t.university.aid}
            value={uni.intl_aid.value ? t.aid[uni.intl_aid.value] : null}
            fact={uni.intl_aid}
            yours={profile.needs_aid ? "нужна" : "не нужна"}
          />
        </tbody>
      </table>
      <p className="mt-2 flex items-center gap-1 text-[11px] text-muted-foreground">
        <Info className="h-3 w-3" /> {t.common.approxGpa}. {t.university.rank}: {rank(uni.world_rank)} ({t.university.rankNote}).
      </p>
    </div>
  );
}

export function University() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const universities = useUniversities();
  const profile = useProfile();
  const recs = useRecommendations();
  const favorites = useFavorites();
  const toggleFavorite = useToggleFavorite();
  const offline = useNetwork((s) => s.offline);
  const explain = useExplain(id, !!profile.data);
  const essays = useEssays();
  const saveProfile = useSaveProfile();
  // A country outside the profile has no saved rec: rate this university with the stateless preview.
  const countryPreview = useCountryPreview(profile.data, universities.data?.find((u) => u.id === id)?.country ?? null);

  if (universities.isPending) return <PageSkeleton />;
  if (universities.isError && !universities.data) return <ErrorState onRetry={() => universities.refetch()} />;
  const uni = universities.data?.find((u) => u.id === id);
  if (!uni) return <EmptyState title={t.university.notFound} action={<Button onClick={() => navigate("/recommendations")}>{t.nav.universities}</Button>} />;

  const rec = recs.data?.recs.find((r) => r.university_id === id);
  const excluded = recs.data?.excluded.find((e) => e.university_id === id);
  const isFav = (favorites.data ?? []).includes(id);
  const p = profile.data;
  const previewRec = countryPreview.data?.recs.find((r) => r.university_id === id);
  const previewExcluded = countryPreview.data?.excluded.find((e) => e.university_id === id);
  const essayCount = (essays.data ?? []).filter((e) => e.university_id === id).length;

  return (
    <div className="space-y-5">
      <button type="button" onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-sm font-semibold text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> {t.common.back}
      </button>

      <header className="space-y-3">
        <h1 className="text-2xl font-bold leading-tight md:text-3xl">{uni.name}</h1>
        <p className="text-sm text-muted-foreground">
          {uni.city}, {countryName(uni.country)} ·{" "}
          <a href={uni.website} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-primary hover:underline">
            {t.university.website} <ExternalLink className="h-3 w-3" />
          </a>
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {rec && <TierBadge tier={rec.tier} />}
          {rec && <ChanceBadge chance={rec.chance} />}
          <div className="flex-1" />
          <Button variant={isFav ? "outline" : "accent"} onClick={() => toggleFavorite.mutate({ id, on: !isFav })} disabled={offline || toggleFavorite.isPending}>
            <Star className={cn(isFav && "fill-accent text-accent")} />
            {isFav ? t.university.inPlan : t.university.addToPlan}
          </Button>
        </div>
      </header>

      {p && !p.countries.includes(uni.country) && (
        <Card className="space-y-3 border-primary/30 bg-primary/5 p-4">
          <SectionTitle className="mb-0 flex items-center gap-2">
            <Globe2 className="h-4 w-4 text-primary" /> {t.university.previewTitle}
          </SectionTitle>
          {countryPreview.isPending ? (
            <Skeleton className="h-16" />
          ) : previewRec || previewExcluded ? (
            <>
              <p className="text-sm text-muted-foreground">
                {previewRec
                  ? t.university.previewText(countryName(uni.country))
                  : t.university.previewExcluded(countryName(uni.country))}
              </p>
              {previewRec && (
                <div className="flex flex-wrap items-center gap-2">
                  <TierBadge tier={previewRec.tier} />
                  <ChanceBadge chance={previewRec.chance} />
                </div>
              )}
              <div className="flex flex-wrap gap-1.5">
                {(previewRec?.reasons ?? previewExcluded?.reasons ?? []).map((r) => (
                  <ReasonChip key={r.code + r.text} reason={r} />
                ))}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">{t.university.notInCountries}</p>
          )}
          <Button
            size="sm"
            onClick={() => saveProfile.mutate(profileToIn(p, { countries: [...p.countries, uni.country] }))}
            disabled={offline || saveProfile.isPending}
          >
            {saveProfile.isPending ? <Loader2 className="animate-spin" /> : <Plus />}
            {saveProfile.isPending ? t.recs.addingCountry : t.recs.addCountry(countryName(uni.country))}
          </Button>
        </Card>
      )}

      {(rec || excluded) && (
        <Card className="space-y-3 p-4">
          <SectionTitle className="mb-0">{rec ? t.university.whyTitle : t.university.excludedTitle}</SectionTitle>
          {explain.isPending ? (
            <Skeleton className="h-12" />
          ) : explain.data ? (
            <div className="space-y-1">
              <p className="text-sm leading-relaxed">{explain.data.summary}</p>
              <GeneratedMark generated={explain.data.generated} />
            </div>
          ) : null}
          <div className="flex flex-wrap gap-1.5">
            {(rec?.reasons ?? excluded?.reasons ?? []).map((r) => (
              <ReasonChip key={r.code + r.text} reason={r} />
            ))}
          </div>
        </Card>
      )}

      {p && (
        <Card className="p-4">
          <SectionTitle>{t.university.requirements}</SectionTitle>
          <Requirements uni={uni} profile={p} />
        </Card>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        <Card className="p-4">
          <SectionTitle className="flex items-center gap-2">
            <CalendarClock className="h-4 w-4" /> {t.university.deadlines}
          </SectionTitle>
          {uni.deadlines.length === 0 ? (
            <p className="text-sm italic text-muted-foreground">{t.common.notPublished}</p>
          ) : (
            <ul className="space-y-2">
              {uni.deadlines.map((d, i) =>
                d.value ? (
                  <li key={i} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span className="font-semibold">{t.deadlineTypes[d.value.type]}</span>
                    <span className="flex items-center gap-2">
                      {shortDate(p ? projectDeadline(d.value.date, p.intake_year) : d.value.date)}
                      <SourceBadge sourceUrl={d.source_url} checkedAt={d.checked_at} isDemo={d.is_demo} />
                    </span>
                  </li>
                ) : null,
              )}
            </ul>
          )}
        </Card>

        <Card className="space-y-4 p-4">
          <div>
            <SectionTitle className="flex items-center gap-2">
              <FileText className="h-4 w-4" /> {t.university.documents}
            </SectionTitle>
            <ul className="list-inside list-disc space-y-1 text-sm">
              {uni.documents.map((d) => (
                <li key={d}>{DOCUMENT_TITLES[d] ?? d}</li>
              ))}
            </ul>
          </div>
          {uni.extra_requirements.length > 0 && (
            <div>
              <p className="mb-1 text-sm font-bold">{t.university.extra}</p>
              <ul className="list-inside list-disc space-y-1 text-sm">
                {uni.extra_requirements.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      </div>

      <div className="flex flex-wrap gap-x-6 gap-y-2">
        {essayCount > 0 && (
          <Link
            to={`/essays?university=${uni.id}`}
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:underline"
          >
            <BookOpen className="h-4 w-4" /> {t.essays.fromUniversity(essayCount)} →
          </Link>
        )}
        <Link to="/compare" className="inline-block text-sm font-semibold text-primary hover:underline">
          {t.nav.compare} →
        </Link>
      </div>
    </div>
  );
}
