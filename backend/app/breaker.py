"""异常调用熔断器（DESIGN §6：错误率 ≥ 阈值且持续 → 熔断）。

进程内滚动窗口实现，够本轮用；多实例部署时下一轮换成基于 Redis/DB 的共享状态。
接真实生成后，在调用 Anthropic 的成功/失败处调用 record()，据错误率自动 open。
"""

import threading
from collections import deque


class CircuitBreaker:
    def __init__(self, threshold: float = 0.2, window: int = 20, min_samples: int = 5):
        self.threshold = threshold
        self.window = window
        self.min_samples = min_samples
        self._events: deque[int] = deque(maxlen=window)
        self._lock = threading.Lock()
        self.forced_open = False

    def record(self, ok: bool) -> None:
        with self._lock:
            self._events.append(1 if ok else 0)

    def error_rate(self) -> float:
        with self._lock:
            n = len(self._events)
            if n == 0:
                return 0.0
            return 1 - sum(self._events) / n

    def is_open(self) -> bool:
        if self.forced_open:
            return True
        with self._lock:
            n = len(self._events)
            if n < self.min_samples:
                return False
            return (1 - sum(self._events) / n) >= self.threshold

    def trip(self) -> None:
        """手动强制熔断（运维/演示用）。"""
        self.forced_open = True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self.forced_open = False


# 全局单例（生成链路共用）。
breaker = CircuitBreaker()
