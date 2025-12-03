import { isAtBottom, isManualScrolling } from "@/utils/sharedRefs";
import React, {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import styles from "./index.module.scss";
// import { debounce } from "lodash";
interface ScrollToBottomButtonProps
  extends React.HTMLAttributes<HTMLDivElement> {
  autoScrollThreshold?: number;
}
interface ScrollToBottomButtonHandles {
  scrollToBottom: (behavior?: ScrollBehavior) => void;
}

const ScrollToBottomButton = forwardRef<
  ScrollToBottomButtonHandles,
  ScrollToBottomButtonProps
>(({ children, autoScrollThreshold = 1, className, ...props }, ref) => {
  const [showButton, setShowButton] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const isScroll = useRef(false);
  const isAutoScrolling = useRef<boolean>(false);
  const scrollTimeout = useRef<NodeJS.Timeout | null>(null);

  // Precise bottom detection
  const checkIsAtBottom = useCallback(() => {
    const container = containerRef.current;
    if (!container) return true;
    // const { scrollTop, scrollHeight, clientHeight } = container;
    // Handle floating point precision: round to integer
    const { scrollTop, scrollHeight, clientHeight } = container;

    // Calculate difference from bottom and take absolute value
    const diff = scrollHeight - (scrollTop + clientHeight);
    const isBottom = Math.abs(diff) <= Math.max(30, autoScrollThreshold);

    isAtBottom.current = isBottom;
    return isAtBottom.current;
  }, [autoScrollThreshold]);
  // Scroll method with lock
  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const container = containerRef.current;
    if (!container) return;
    // Clear previous timer
    if (scrollTimeout.current) {
      clearTimeout(scrollTimeout.current);
    }
    isScroll.current = false;
    isAutoScrolling.current = true;
    setShowButton(false);
    // container.style.scrollBehavior = behavior;
    container.scrollTop = container.scrollHeight;
    container.style.scrollBehavior = "auto";
    isAtBottom.current = true;
    isManualScrolling.current = true;

    // Set new timer
    scrollTimeout.current = setTimeout(() => {
      if (container) {
        isAutoScrolling.current = false;
        // isManualScrolling.current = true;
      }
      // Clean up timer reference
      scrollTimeout.current = null;
    }, 0);
  }, []);
  // Optimized scroll handling
  const handleScroll = useCallback(() => {
    requestAnimationFrame(() => {
      if (isAutoScrolling.current) return;
      setShowButton(!checkIsAtBottom());
      isScroll.current = !checkIsAtBottom();
      isManualScrolling.current = false;
    });
  }, [checkIsAtBottom]);

  useImperativeHandle(ref, () => ({
    scrollToBottom,
    checkIsAtBottom,
  }));

  return (
    <div
      {...props}
      ref={containerRef}
      className={`${styles.scrollRoot} ${className}`}
      onScroll={handleScroll}
    >
      {children}

      <div
        className={styles.scrollAnchor}
        style={{ position: "absolute", bottom: 0 }}
      />

      {isScroll.current && showButton && (
        <button
          className={styles.scrollButton}
          onClick={() => scrollToBottom("auto")}
          style={{
            position: "sticky",
            bottom: "20px",
            float: "right",
            animation: `${styles.fadeIn} 0.3s forwards`,
          }}
        >
          ↓
        </button>
      )}
    </div>
  );
});
export default ScrollToBottomButton;
