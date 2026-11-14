"use client";

import { Plus } from "lucide-react";
import { useId, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { SidebarMenuButton } from "@/components/ui/sidebar";
import { addPortfolioStock } from "@/server/add-portfolio-stock";

import { StockPicker } from "../stock-picker";

export function AddStockDialog({ sidebar = true, initialTicker = "" }: { sidebar?: boolean; initialTicker?: string }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [ticker, setTicker] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  function changeOpen(value: boolean) {
    if (pending) return;
    setError("");
    setTicker(initialTicker);
    setOpen(value);
  }

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogTrigger asChild>
        {sidebar ? (
          <SidebarMenuButton tooltip="Add stock">
            <Plus />
            <span>Add stock</span>
          </SidebarMenuButton>
        ) : (
          <Button size="sm" variant={initialTicker ? "outline" : "default"} aria-label={initialTicker ? `Add ${initialTicker} to portfolio` : undefined}>
            <Plus /> {initialTicker ? <span className="hidden sm:inline">Add to portfolio</span> : "Add stock"}
          </Button>
        )}
      </DialogTrigger>
      <DialogContent aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>Add stock to portfolio</DialogTitle>
        </DialogHeader>
        <form
          className="flex flex-col gap-4"
          onSubmit={async (event) => {
            event.preventDefault();
            if (pending) return;
            const form = new FormData(event.currentTarget);
            setPending(true);
            setError("");
            try {
              const result = await addPortfolioStock(form);
              if (result.error) {
                setError(result.error);
              } else {
                toast.success(`${result.ticker} added to your portfolio.`);
                setOpen(false);
              }
            } catch {
              setError("Couldn’t save the stock. Try again.");
            } finally {
              setPending(false);
            }
          }}
        >
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor={id}>Stock</FieldLabel>
              <input type="hidden" name="ticker" value={ticker} />
              <StockPicker
                id={id}
                ticker={ticker}
                disabled={pending}
                onSelect={(symbol) => {
                  setTicker(symbol);
                  setError("");
                }}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor={`${id}-quantity`}>Shares held (optional)</FieldLabel>
              <Input
                id={`${id}-quantity`}
                name="quantity"
                inputMode="decimal"
                placeholder="e.g. 2.5"
                disabled={pending}
              />
            </Field>
            {error && <FieldError>{error}</FieldError>}
          </FieldGroup>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline" disabled={pending}>
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={pending || !ticker}>
              {pending ? "Adding…" : "Add stock"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
