import React from 'react';
import * as SwitchPrimitives from '@radix-ui/react-switch';
import { cn } from '@/utilfunctions/shadcn';

const Switch = ({ className, ref, ...props }) => (
  <SwitchPrimitives.Root
    className={cn(
      `peer focus-visible:fmtm-ring-offset-background data-[state=checked]:fmtm-bg-primary-900 fmtm-inline-flex fmtm-h-[18px] fmtm-w-[30px] fmtm-shrink-0 fmtm-cursor-pointer
        fmtm-items-center fmtm-rounded-full fmtm-border-2 fmtm-border-transparent
        fmtm-transition-colors  focus-visible:fmtm-outline-none focus-visible:fmtm-ring-2
        focus-visible:fmtm-ring-offset-2 disabled:fmtm-cursor-not-allowed disabled:fmtm-opacity-50
        data-[state=unchecked]:fmtm-bg-grey-400 `,
      className,
    )}
    {...props}
    ref={ref}
  >
    <SwitchPrimitives.Thumb
      className={cn(
        `fmtm-pointer-events-none fmtm-block fmtm-h-[14px] fmtm-w-[14px] fmtm-rounded-full fmtm-bg-white
          fmtm-shadow-lg fmtm-ring-0 fmtm-transition-transform
          data-[state=checked]:fmtm-translate-x-3 data-[state=unchecked]:fmtm-translate-x-0`,
      )}
    />
  </SwitchPrimitives.Root>
);
Switch.displayName = SwitchPrimitives.Root.displayName;

export default Switch;
