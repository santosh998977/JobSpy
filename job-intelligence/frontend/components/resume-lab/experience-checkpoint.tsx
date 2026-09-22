"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

type ExperienceCheckpointProps = {
  open: boolean;
  keywords: string[];
  notes: string;
  saving: boolean;
  onNotesChange: (notes: string) => void;
  onSaveAndGenerate: () => void;
  onContinue: () => void;
  onCancel: () => void;
};

export function ExperienceCheckpoint({
  open, keywords, notes, saving, onNotesChange, onSaveAndGenerate, onContinue, onCancel,
}: ExperienceCheckpointProps) {
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    if (!open) setConfirmed(false);
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) onCancel(); }}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Important job keywords are missing</DialogTitle>
          <DialogDescription>
            Add only experience you actually have. These notes become source facts for this profile and can improve the tailored resume.
          </DialogDescription>
        </DialogHeader>
        <div className="flex max-h-28 flex-wrap gap-2 overflow-y-auto">
          {keywords.map((keyword) => <span key={keyword} className="rounded-full border px-3 py-1 text-xs">{keyword}</span>)}
        </div>
        <Textarea
          value={notes}
          onChange={(event) => onNotesChange(event.target.value)}
          maxLength={6000}
          className="min-h-40"
          placeholder="Example: Built Spring Boot REST APIs and wrote JUnit tests for the order-processing service."
        />
        <p className="text-xs text-muted-foreground">{notes.length}/6000 characters. Include context and results; do not list keywords alone.</p>
        <label className="flex items-start gap-2 text-sm">
          <input className="mt-1" type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
          I confirm these notes describe my real experience.
        </label>
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="outline" onClick={onCancel} disabled={saving}>Cancel</Button>
          <Button variant="outline" onClick={onContinue} disabled={saving}>Continue Without Adding</Button>
          <Button onClick={onSaveAndGenerate} disabled={saving || !notes.trim() || !confirmed}>
            {saving ? "Saving..." : "Save & Generate"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
