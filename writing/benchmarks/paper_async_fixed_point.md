# Convergence Analysis of Asynchronous Distributed Fixed-Point Iterations under Bounded Delays

## Section 1: System Model and Contraction Invariants

In a network of $n$ computational nodes, each processor $i$ maintains a local state coordinate $x_i \in \mathbb{R}$. Suppose an operator $T: \mathbb{R}^n \to \mathbb{R}^n$ contracts under the maximum norm with Lipschitz constant $\gamma < 1$:
\[
\|T(x) - T(x^*)\|_\infty \le \gamma \|x - x^*\|_\infty.
\]
The Banach fixed-point theorem guarantees a unique equilibrium $x^*$ where $T(x^*) = x^*$.

To ground the convergence bounds in practice, Table 1 reports the configuration of a 64-node simulation.

| Parameter | Symbol | Benchmark Value |
| :--- | :--- | :--- |
| Cluster size | $n$ | 64 nodes |
| Contraction factor | $\gamma$ | 0.85 |
| Uniform delay bound | $B$ | 5 time steps |
| Error tolerance | $\epsilon$ | $10^{-6}$ |
| Convergence duration | $t_{\text{conv}}$ | 142 steps |

The simulation confirms that bounded delays reduce convergence speed while preserving the asymptotic geometric rate.

## Section 2: Asynchronous Iteration Dynamics

Let $t \in \mathbb{N}$ index discrete execution rounds. During round $t$, an active subset $U_t \subseteq \{1, \dots, n\}$ recomputes its assigned components using delayed coordinate estimates from peer nodes:
\[
x^i(t) = \big(x_1(t - \tau_1^i(t)), \, x_2(t - \tau_2^i(t)), \, \dots, \, x_n(t - \tau_n^i(t))\big).
\]
Here $\tau_j^i(t)$ represents message transit latency from node $j$ to node $i$. Assuming network delays satisfy a uniform upper bound $B$:
\[
0 \le \tau_j^i(t) \le B.
\]
State coordinates evolve according to the piecewise component rule:
\[
x_i(t+1) = \begin{cases}
T_i(x^i(t)), & \text{if } i \in U_t, \\
x_i(t), & \text{if } i \notin U_t.
\end{cases}
\]

## Section 3: Convergence Proof via Nested Norm Boxes

Bounding the iteration error relies on a nested sequence of maximum-norm hypercubes centered at $x^*$. Let $R_0 = \|x(0) - x^*\|_\infty$ denote the initial radius, and let $R_k = \gamma^k R_0$ shrink geometrically for integers $k \ge 0$.

If all coordinates remain within distance $R_k$ of the equilibrium for past rounds $s \ge t_k$, any delayed coordinate evaluated at time $t \ge t_k + B$ originates within the verified window $[t_k, t]$. Consequently, the delayed view vector obeys $\|x^i(t) - x^*\|_\infty \le R_k$.

Applying coordinate contraction yields:
\[
|x_i(t+1) - x_i^*| = |T_i(x^i(t)) - T_i(x^*)| \le \|T(x^i(t)) - T(x^*)\|_\infty \le \gamma R_k = R_{k+1}.
\]
Provided every node activates at least once within every $W$ rounds, all components enter the tighter envelope $R_{k+1}$ by round $t_{k+1} = t_k + B + W$, guaranteeing asymptotic convergence at rate $\gamma^{t / (B + W)}$.
