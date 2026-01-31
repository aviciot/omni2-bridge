import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, style, ...props }, ref) => {
    return (
      <input
        type={type}
        style={{
          backgroundColor: '#ffffff',
          color: '#000000',
          border: '1px solid #d1d5db',
          padding: '8px 12px',
          borderRadius: '8px',
          fontSize: '16px',
          ...style
        }}
        className={cn(
          "flex h-10 w-full focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
