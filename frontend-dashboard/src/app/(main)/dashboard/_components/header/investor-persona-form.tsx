"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Field, FieldContent, FieldDescription, FieldLabel, FieldLegend, FieldSet } from "@/components/ui/field";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { investorPersonas } from "@/data/investor-personas";
import { authClient } from "@/lib/auth-client";

export function InvestorPersonaForm({ savedPersona }: { savedPersona?: string | null }) {
  const router = useRouter();
  const [choice, setChoice] = useState(savedPersona ?? "");
  const [saving, startSaving] = useTransition();

  function save() {
    if (!choice || choice === savedPersona || saving) return;
    startSaving(async () => {
      try {
        const { error } = await authClient.updateUser({ investorPersona: choice });
        if (error) throw new Error();
        router.refresh();
        toast.success("Investor persona saved.");
      } catch {
        toast.error("Couldn’t save your investor persona. Try again.");
      }
    });
  }

  return (
    <form action={save} className="flex flex-col items-start gap-4">
      <FieldSet className="w-full">
        <FieldLegend id="persona-legend">Choose a fictional investor for your simulation.</FieldLegend>
        <RadioGroup aria-labelledby="persona-legend" value={choice} onValueChange={setChoice} disabled={saving}>
          {investorPersonas.map(({ id, label, description }) => (
            <Field orientation="horizontal" key={id}>
              <RadioGroupItem id={id} value={id} aria-describedby={`${id}-description`} />
              <FieldContent>
                <FieldLabel htmlFor={id}>{label}</FieldLabel>
                <FieldDescription id={`${id}-description`}>{description}</FieldDescription>
              </FieldContent>
            </Field>
          ))}
        </RadioGroup>
      </FieldSet>
      <Button type="submit" size="sm" disabled={!choice || choice === savedPersona || saving}>
        {saving ? "Saving…" : "Save changes"}
      </Button>
    </form>
  );
}
