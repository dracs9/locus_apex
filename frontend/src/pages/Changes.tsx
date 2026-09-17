import { AnimatePresence, motion } from "framer-motion";
import { ArrowDown, ArrowRight, ArrowUp, CheckCircle2, ListMinus, ListPlus, Minus, Plus } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { useLatestChanges, useRecommendations, useUniversityMap } from "@/api/hooks";
import type { Chance, Tier } from "@/api/types";
import { ChanceBadge, TierBadge } from "@/components/ds/badges";
import { Card, PageHeader, SectionTitle } from "@/components/ds/Card";
import { CardsSkeleton, EmptyState, ErrorState } from "@/components/ds/states";
import { Button } from "@/components/ui/button";
import { t } from "@/i18n/ru";
import { shortDate } from "@/lib/format";

const TIER_RANK: Record<Tier, number> = { safety: 0, target: 1, dream: 2 };
const CHANCE_RANK: Record<Chance, number> = { low: 0, medium: 1, high: 2 };

function Group({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <section>
      <SectionTitle className="flex items-center gap-2">
        {icon}
        {title}
      </SectionTitle>
      <motion.ul layout className="space-y-2">
        <AnimatePresence initial>{children}</AnimatePresence>
      </motion.ul>
    </section>
  );
}

function Row({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 380, damping: 30, delay }}
      className="flex flex-wrap items-center gap-2 rounded-lg border bg-card px-4 py-3 text-sm"
    >
      {children}
    </motion.li>
  );
}

export function Changes() {
  const changes = useLatestChanges();
  const recs = useRecommendations();
  const { map } = useUniversityMap();
  const name = (id: string) => (
    <Link to={`/university/${id}`} className="font-semibold hover:underline">
      {map.get(id)?.name ?? id}
    </Link>
  );
  const recOf = (id: string) => recs.data?.recs.find((r) => r.university_id === id);
  const stepTitle = (id: string) => id.replace(/^apply:([^:]+):.*/, (_, u: string) => `Заявка: ${map.get(u)?.name ?? u}`);

  if (changes.isPending) return <CardsSkeleton />;
  if (changes.isError && !changes.data) return <ErrorState onRetry={() => changes.refetch()} />;
  const diff = changes.data?.diff;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t.changes.title}
        subtitle={changes.data?.at ? shortDate(changes.data.at.slice(0, 10)) : undefined}
        actions={
          <Button size="sm" asChild>
            <Link to="/recommendations">
              {t.changes.backToRoute} <ArrowRight />
            </Link>
          </Button>
        }
      />

      {!diff ? (
        <EmptyState title={t.changes.none} />
      ) : (
        <>
          <Card className="border-primary/30 bg-primary/5 p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-primary">{t.changes.cause}</p>
            <p className="mt-1 font-semibold">{diff.cause}</p>
          </Card>

          {diff.added.length + diff.removed.length + diff.tier_changed.length + diff.chance_changed.length === 0 && (
            <p className="text-sm text-muted-foreground">{t.changes.nothingChanged}</p>
          )}

          {diff.added.length > 0 && (
            <Group title={t.changes.added} icon={<Plus className="h-4 w-4 text-plus" />}>
              {diff.added.map((id, i) => {
                const rec = recOf(id);
                return (
                  <Row key={id} delay={i * 0.05}>
                    {name(id)}
                    <span className="flex-1" />
                    {rec && <TierBadge tier={rec.tier} />}
                  </Row>
                );
              })}
            </Group>
          )}

          {diff.removed.length > 0 && (
            <Group title={t.changes.removed} icon={<Minus className="h-4 w-4 text-blocker" />}>
              {diff.removed.map((id, i) => {
                const why = recs.data?.excluded.find((e) => e.university_id === id)?.reasons[0]?.text;
                return (
                  <Row key={id} delay={i * 0.05}>
                    <span className="line-through decoration-blocker/60">{name(id)}</span>
                    {why && <span className="w-full text-xs text-muted-foreground">{why}</span>}
                  </Row>
                );
              })}
            </Group>
          )}

          {diff.tier_changed.length > 0 && (
            <Group title={t.changes.tierChanged} icon={<ArrowUp className="h-4 w-4 text-primary" />}>
              {diff.tier_changed.map((c, i) => (
                <Row key={c.id} delay={i * 0.05}>
                  {name(c.id)}
                  <span className="flex-1" />
                  <TierBadge tier={c.from} className="opacity-60" />
                  {TIER_RANK[c.to] < TIER_RANK[c.from] ? <ArrowUp className="h-4 w-4 text-plus" /> : <ArrowDown className="h-4 w-4 text-risk" />}
                  <motion.span initial={{ scale: 0.6 }} animate={{ scale: 1 }} transition={{ delay: 0.25 + i * 0.05 }}>
                    <TierBadge tier={c.to} />
                  </motion.span>
                </Row>
              ))}
            </Group>
          )}

          {diff.chance_changed.length > 0 && (
            <Group title={t.changes.chanceChanged} icon={<ArrowUp className="h-4 w-4 text-primary" />}>
              {diff.chance_changed.map((c, i) => (
                <Row key={c.id} delay={i * 0.05}>
                  {name(c.id)}
                  <span className="flex-1" />
                  <ChanceBadge chance={c.from} className="opacity-60" />
                  {CHANCE_RANK[c.to] > CHANCE_RANK[c.from] ? <ArrowUp className="h-4 w-4 text-plus" /> : <ArrowDown className="h-4 w-4 text-risk" />}
                  <ChanceBadge chance={c.to} />
                </Row>
              ))}
            </Group>
          )}

          {diff.gaps_closed.length > 0 && (
            <Group title={t.changes.gapsClosed} icon={<CheckCircle2 className="h-4 w-4 text-plus" />}>
              {diff.gaps_closed.map((g, i) => (
                <Row key={g.id + g.code} delay={i * 0.04}>
                  {name(g.id)}
                  <span className="text-muted-foreground">— {t.gapCodes[g.code] ?? g.code}</span>
                </Row>
              ))}
            </Group>
          )}

          {(diff.roadmap_added.length > 0 || diff.roadmap_removed.length > 0) && (
            <div className="grid gap-4 md:grid-cols-2">
              {diff.roadmap_added.length > 0 && (
                <Group title={t.changes.roadmapAdded} icon={<ListPlus className="h-4 w-4 text-plus" />}>
                  {diff.roadmap_added.map((id, i) => (
                    <Row key={id} delay={i * 0.03}>
                      {stepTitle(id)}
                    </Row>
                  ))}
                </Group>
              )}
              {diff.roadmap_removed.length > 0 && (
                <Group title={t.changes.roadmapRemoved} icon={<ListMinus className="h-4 w-4 text-muted-foreground" />}>
                  {diff.roadmap_removed.map((id, i) => (
                    <Row key={id} delay={i * 0.03}>
                      <span className="text-muted-foreground line-through">{stepTitle(id)}</span>
                    </Row>
                  ))}
                </Group>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
