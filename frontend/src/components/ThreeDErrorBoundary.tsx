import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
  /** Optional fallback UI shown when the 3D canvas throws. Defaults to null (invisible). */
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * Wraps any Three.js <Canvas> so that a WebGL / drei error is caught here
 * instead of unmounting the entire React tree.
 */
export class ThreeDErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    // Log for debugging; never crash the outer app.
    console.warn("[3D canvas error — caught by ThreeDErrorBoundary]", error.message);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? null;
    }
    return this.props.children;
  }
}
