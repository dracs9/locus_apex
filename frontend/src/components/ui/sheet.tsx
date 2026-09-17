import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

const Sheet = DialogPrimitive.Root;
const SheetTrigger = DialogPrimitive.Trigger;
const SheetClose = DialogPrimitive.Close;

const SheetContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & { side?: "bottom" | "right" }
>(({ className, children, side = "bottom", ...props }, ref) => (
  <DialogPrimitive.Portal>
    <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:fade-out-0" />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed z-50 flex flex-col gap-4 bg-card p-5 shadow-2xl outline-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:duration-300 data-[state=closed]:duration-200",
        side === "bottom" &&
          "inset-x-0 bottom-0 max-h-[92dvh] overflow-y-auto rounded-t-xl pb-[calc(env(safe-area-inset-bottom)+1.25rem)] data-[state=open]:slide-in-from-bottom data-[state=closed]:slide-out-to-bottom md:inset-x-auto md:left-1/2 md:w-[520px] md:-translate-x-1/2",
        side === "right" &&
          "inset-y-0 right-0 h-full w-full max-w-md overflow-y-auto data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right",
        className,
      )}
      {...props}
    >
      {side === "bottom" && <div className="mx-auto -mt-2 h-1.5 w-10 rounded-full bg-muted md:hidden" aria-hidden />}
      {children}
      <DialogPrimitive.Close className="absolute right-3 top-3 rounded-full p-2 text-muted-foreground hover:bg-muted">
        <X className="h-4 w-4" />
        <span className="sr-only">Закрыть</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPrimitive.Portal>
));
SheetContent.displayName = "SheetContent";

const SheetTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title ref={ref} className={cn("pr-8 font-display text-lg font-bold", className)} {...props} />
));
SheetTitle.displayName = "SheetTitle";

const SheetDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description ref={ref} className={cn("text-sm text-muted-foreground", className)} {...props} />
));
SheetDescription.displayName = "SheetDescription";

export { Sheet, SheetClose, SheetContent, SheetDescription, SheetTitle, SheetTrigger };
