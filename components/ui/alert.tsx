import * as React from "react";
import * as AlertDialogPrimitive from "@radix-ui/react-alert-dialog";
import { cn } from "@/lib/utils";

const Alert = AlertDialogPrimitive.Root;
const AlertTrigger = AlertDialogPrimitive.Trigger;
const AlertContent = React.forwardRef<
React.ElementRef<typeof AlertDialogPrimitive.Content>,
React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Content>
>(({ className, ...props }, ref) => (
    <AlertDialogPrimitive.Content
    ref={ref}
    className={cn(
        "fixed z-50 grid w-full max-w-lg scale-100 gap-4 border border-gray-200 bg-white p-6 opacity-100 shadow-lg animate-in fade-in-90 slide-in-from-bottom-10 md:w-full",
        className
    )}
    {...props}
    />
));
AlertContent.displayName = AlertDialogPrimitive.Content.displayName;

const AlertTitle = React.forwardRef<
React.ElementRef<typeof AlertDialogPrimitive.Title>,
React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Title>
>(({ className, ...props }, ref) => (
    <AlertDialogPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold text-gray-900", className)}
    {...props}
    />
));
AlertTitle.displayName = AlertDialogPrimitive.Title.displayName;

const AlertDescription = React.forwardRef<
React.ElementRef<typeof AlertDialogPrimitive.Description>,
React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Description>
>(({ className, ...props }, ref) => (
    <AlertDialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-gray-500", className)}
    {...props}
    />
));
AlertDescription.displayName = AlertDialogPrimitive.Description.displayName;

export { Alert, AlertTrigger, AlertContent, AlertTitle, AlertDescription };
