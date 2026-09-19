import { FlaskConical, Loader2, Moon, Pencil, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { useLoadDemo, useReset } from "@/api/hooks";
import { Card, PageHeader } from "@/components/ds/Card";
import { useProfileEditor } from "@/components/profile/ProfileEditorSheet";
import { Button } from "@/components/ui/button";
import { Label, Switch } from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { useOnboarding } from "@/store/onboarding";
import { useNetwork, useUi } from "@/store/ui";

export function Settings() {
  const navigate = useNavigate();
  const reset = useReset();
  const demo = useLoadDemo();
  const { theme, setTheme, resetCompare } = useUi();
  const resetDraft = useOnboarding((s) => s.reset);
  const openEditor = useProfileEditor((s) => s.setOpen);
  const offline = useNetwork((s) => s.offline);

  const onReset = async () => {
    if (!window.confirm(t.settings.resetConfirm)) return;
    await reset.mutateAsync();
    resetDraft();
    resetCompare();
    toast.success(t.settings.resetDone);
    navigate("/", { replace: true });
  };

  const onDemo = async () => {
    if (!window.confirm(t.settings.demoConfirm)) return;
    await demo.mutateAsync(undefined);
    resetCompare();
    toast.success(t.settings.demoDone);
    navigate("/passport");
  };

  return (
    <div className="space-y-4">
      <PageHeader title={t.settings.title} />

      <Card className="divide-y">
        <div className="flex items-center justify-between gap-3 p-4">
          <Label htmlFor="theme" className="flex items-center gap-2">
            <Moon className="h-4 w-4" /> {t.settings.theme}
          </Label>
          <Switch id="theme" checked={theme === "dark"} onCheckedChange={(v) => setTheme(v ? "dark" : "light")} />
        </div>
        <button type="button" onClick={() => openEditor(true)} disabled={offline} className="flex w-full items-center gap-2 p-4 text-left text-sm font-semibold hover:bg-muted disabled:opacity-50">
          <Pencil className="h-4 w-4" /> {t.profileEditor.title}
        </button>
      </Card>

      <Card className="space-y-3 p-4">
        <Button variant="outline" className="w-full justify-start" onClick={onDemo} disabled={offline || demo.isPending}>
          {demo.isPending ? <Loader2 className="animate-spin" /> : <FlaskConical />} {t.settings.demo}
        </Button>
        <Button variant="destructive" className="w-full justify-start" onClick={onReset} disabled={offline || reset.isPending}>
          {reset.isPending ? <Loader2 className="animate-spin" /> : <Trash2 />} {t.settings.reset}
        </Button>
      </Card>

      <p className="text-xs text-muted-foreground">{t.settings.about}</p>
    </div>
  );
}
