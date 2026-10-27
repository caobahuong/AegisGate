"use client";

import { useEffect, useRef } from "react";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "area[href]",
  'input:not([disabled]):not([type="hidden"])',
  "select:not([disabled])",
  "textarea:not([disabled])",
  "button:not([disabled])",
  "iframe",
  "object",
  "embed",
  '[tabindex]:not([tabindex="-1"])',
  "[contenteditable]",
].join(", ");

const INPUT_SELECTOR = [
  'input:not([disabled]):not([type="hidden"])',
  "select:not([disabled])",
  "textarea:not([disabled])",
].join(", ");

interface UseFocusTrapOptions {
  isActive: boolean;
  onClose?: () => void;
  initialFocusRef?: React.RefObject<HTMLElement>;
}

export function useFocusTrap<T extends HTMLElement = HTMLDivElement>({
  isActive,
  onClose,
  initialFocusRef,
}: UseFocusTrapOptions) {
  const containerRef = useRef<T>(null);
  const triggerRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const hasFocusedRef = useRef(false);

  useEffect(() => {
    if (!isActive) {
      hasFocusedRef.current = false;
      return;
    }

    // Save the element that triggered the modal/drawer before opening
    if (!hasFocusedRef.current) {
      triggerRef.current = document.activeElement as HTMLElement | null;
    }

    // Lock body scroll
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const container = containerRef.current;
    if (container && !hasFocusedRef.current) {
      hasFocusedRef.current = true;

      // Do not steal focus if focus is already within container
      if (!container.contains(document.activeElement)) {
        if (initialFocusRef?.current) {
          initialFocusRef.current.focus();
        } else {
          // Prefer focusing the first interactive form input rather than the top close 'X' button
          const firstInput = container.querySelector<HTMLElement>(INPUT_SELECTOR);
          if (firstInput) {
            firstInput.focus();
          } else {
            const focusables = container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
            if (focusables.length > 0) {
              focusables[0].focus();
            } else {
              container.focus();
            }
          }
        }
      }
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current?.();
        return;
      }

      if (event.key === "Tab" && container) {
        const focusables = Array.from(
          container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
        ).filter((el) => el.offsetParent !== null); // Visible only

        if (focusables.length === 0) {
          event.preventDefault();
          return;
        }

        const first = focusables[0];
        const last = focusables[focusables.length - 1];

        if (event.shiftKey) {
          if (document.activeElement === first) {
            event.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            event.preventDefault();
            first.focus();
          }
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;
      // Restore focus to trigger element only when closing
      if (triggerRef.current && typeof triggerRef.current.focus === "function") {
        triggerRef.current.focus();
      }
    };
  }, [isActive, initialFocusRef]);

  return containerRef;
}
