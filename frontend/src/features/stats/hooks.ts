import { useEffect, useState } from 'react';

interface QueryState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useStatsQuery<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  dependencies: readonly unknown[],
): QueryState<T> {
  const [state, setState] = useState<QueryState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    const controller = new AbortController();

    setState((current) => ({
      ...current,
      loading: true,
      error: null,
    }));

    loader(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setState({
            data,
            loading: false,
            error: null,
          });
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setState({
          data: null,
          loading: false,
          error:
            error instanceof Error
              ? error.message
              : '통계 조회에 실패했습니다.',
        });
      });

    return () => {
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  return state;
}
