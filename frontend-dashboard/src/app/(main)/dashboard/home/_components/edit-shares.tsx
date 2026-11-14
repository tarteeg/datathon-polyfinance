"use client";

import { Pencil } from "lucide-react";
import { useId, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { updatePortfolioShares } from "@/server/add-portfolio-stock";

export function EditShares({
  ticker,
  quantity,
  mobile = false,
}: {
  ticker: string;
  quantity: string | null;
  mobile?: boolean;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!pending) {
          setError("");
          setOpen(next);
        }
      }}
    >
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size={mobile ? "icon-sm" : "sm"}
          className={mobile ? "sm:hidden" : "tabular-nums"}
          aria-label={`Edit shares for ${ticker}`}
        >
          {!mobile && (quantity ?? "Add shares")}
          <Pencil />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit shares for {ticker}</DialogTitle>
          <DialogDescription>
            Clear the quantity to keep this stock in your portfolio without including it in your holdings total.
          </DialogDescription>
        </DialogHeader>
        <form
          className="flex flex-col gap-4"
          onSubmit={async (event) => {
            event.preventDefault();
            if (pending) return;
            const value = String(new FormData(event.currentTarget).get("quantity") ?? "");
            setPending(true);
            setError("");
            try {
              const result = await updatePortfolioShares(ticker, value);
              if (result.error) setError(result.error);
              else {
                toast.success(`Shares updated for ${ticker}.`);
                setOpen(false);
              }
            } catch {
              setError("Couldn’t save your shares. Try again.");
            } finally {
              setPending(false);
            }
          }}
        >
          <Field>
            <FieldLabel htmlFor={id}>Total shares held</FieldLabel>
            <Input
              id={id}
              name="quantity"
              inputMode="decimal"
              defaultValue={quantity ?? ""}
              placeholder="e.g. 2.5"
              disabled={pending}
            />
            {error && <FieldError>{error}</FieldError>}
          </Field>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline" disabled={pending}>
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={pending}>
              {pending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
