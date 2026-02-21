```markdown
# Electrostatic Potential and Energy (Extracts from Chapter 2)

## 2.7 Potential Energy of a System of Charges

The potential energy of a system of two charges \( q_1 \) and \( q_2 \) is given by

$$U = \frac{1}{4\pi\epsilon_0} \frac{q_1q_2}{r_{12}} \tag{2.22}$$

where \( r_{12} \) is the distance between the charges. This work gets stored in the form of potential energy of the system because electrostatic force is conservative.

- If \( q_1q_2 > 0 \) (like charges), potential energy is positive. This is expected, since work must be done against the repulsive force to bring the charges from infinity to a finite distance apart.
- If \( q_1q_2 < 0 \) (unlike charges), potential energy is negative. Work is done *by* the field (or negative work is required) to bring the charges from infinity to their locations.

Equation (2.22) is independent of the path taken to assemble the charges and is valid for any sign of the charges.

---

### Potential Energy of Three Charges

For a system of three charges \( q_1 \), \( q_2 \), and \( q_3 \) located at \( \mathbf{r}_1 \), \( \mathbf{r}_2 \), and \( \mathbf{r}_3 \) respectively, the total potential energy is obtained by assembling the charges step by step:

1.  Bring \( q_1 \) from infinity to \( \mathbf{r}_1 \): Work done = 0.
2.  Bring \( q_2 \) from infinity to \( \mathbf{r}_2 \):
    $$W_2 = q_2 V_1(\mathbf{r}_2) = \frac{1}{4\pi\epsilon_0} \frac{q_1q_2}{r_{12}} \tag{2.23}$$
3.  Bring \( q_3 \) from infinity to \( \mathbf{r}_3 \). The potential at \( \mathbf{r}_3 \) due to \( q_1 \) and \( q_2 \) is:
    $$V_{1,2}(\mathbf{r}_3) = \frac{1}{4\pi\epsilon_0} \left( \frac{q_1}{r_{13}} + \frac{q_2}{r_{23}} \right) \tag{2.24}$$
    The work done in this step is:
    $$W_3 = q_3 V_{1,2}(\mathbf{r}_3) = \frac{1}{4\pi\epsilon_0} \left( \frac{q_1q_3}{r_{13}} + \frac{q_2q_3}{r_{23}} \right) \tag{2.25}$$

The total potential energy \( U \) of the system is the sum of the work done in all steps:

$$U = \frac{1}{4\pi\epsilon_0} \left( \frac{q_1q_2}{r_{12}} + \frac{q_1q_3}{r_{13}} + \frac{q_2q_3}{r_{23}} \right) \tag{2.26}$$

This expression is independent of the order in which the charges are assembled and is characteristic of the final configuration.

---

## Example 2.4

Four charges are arranged at the corners of a square ABCD of side \( d \), as shown in Fig. 2.15.
(a) Find the work required to put together this arrangement.
(b) A charge \( q_0 \) is brought to the centre E of the square, the four charges being held fixed at its corners. How much extra work is needed to do this?

**Solution**

**(a)** The work done depends only on the final arrangement. We calculate it by assembling the charges in the order: \(+q\) at A, then \(-q\) at B, then \(+q\) at C, and finally \(-q\) at D.

(i) Work to bring \(+q\) to A (no other charges): \(W_1 = 0\)

(ii) Work to bring \(-q\) to B with \(+q\) at A:
$$W_2 = (-q) \times V_A(B) = (-q) \times \left( \frac{+q}{4\pi\epsilon_0 d} \right) = -\frac{q^2}{4\pi\epsilon_0 d}$$

(iii) Work to bring \(+q\) to C with \(+q\) at A and \(-q\) at B:
$$W_3 = (+q) \times V_{A,B}(C) = q \left( \frac{+q}{4\pi\epsilon_0 d\sqrt{2}} + \frac{-q}{4\pi\epsilon_0 d} \right)$$
$$W_3 = \frac{q^2}{4\pi\epsilon_0 d} \left( \frac{1}{\sqrt{2}} - 1 \right) = -\frac{q^2}{4\pi\epsilon_0 d} \left(1 - \frac{1}{\sqrt{2}}\right)$$

(iv) Work to bring \(-q\) to D with \(+q\) at A, \(-q\) at B, and \(+q\) at C:
$$W_4 = (-q) \times V_{A,B,C}(D)$$
The potential at D due to charges at A (\(+q\)), B (\(-q\)), and C (\(+q\)) is:
$$V(D) = \frac{1}{4\pi\epsilon_0} \left( \frac{+q}{d} + \frac{-q}{d\sqrt{2}} + \frac{+q}{d} \right) = \frac{q}{4\pi\epsilon_0 d} \left( 2 - \frac{1}{\sqrt{2}} \right)$$
Therefore,
$$W_4 = -q \times \frac{q}{4\pi\epsilon_0 d} \left( 2 - \frac{1}{\sqrt{2}} \right) = -\frac{q^2}{4\pi\epsilon_0 d} \left( 2 - \frac{1}{\sqrt{2}} \right)$$

The total work required is the sum of the work done in all steps:
$$W = W_1 + W_2 + W_3 + W_4$$
$$W = 0 + \left(-\frac{q^2}{4\pi\epsilon_0 d}\right) + \left[-\frac{q^2}{4\pi\epsilon_0 d} \left(1 - \frac{1}{\sqrt{2}}\right)\right] + \left[-\frac{q^2}{4\pi\epsilon_0 d} \left(2 - \frac{1}{\sqrt{2}}\right)\right]$$
$$W = -\frac{q^2}{4\pi\epsilon_0 d} \left[ 0 + 1 + \left(1 - \frac{1}{\sqrt{2}}\right) + \left(2 - \frac{1}{\sqrt{2}}\right) \right]$$
$$W = -\frac{q^2}{4\pi\epsilon_0 d} \left(4 - \sqrt{2}\right)$$

This total work is, by definition, the electrostatic potential energy of the charge arrangement.

**(b)** The extra work needed to bring charge \( q_0 \) to the centre E is \( W_{\text{extra}} = q_0 \times V(E) \), where \( V(E) \) is the potential at E due to the four fixed corner charges.

The distance from each corner to the centre E is \( \frac{d}{\sqrt{2}} \). The potential at E is the sum of potentials from each charge:
$$V(E) = \frac{1}{4\pi\epsilon_0} \left( \frac{+q}{d/\sqrt{2}} + \frac{-q}{d/\sqrt{2}} + \frac{+q}{d/\sqrt{2}} + \frac{-q}{d/\sqrt{2}} \right) = 0$$

Since \( V(E) = 0 \), the extra work required is \( W_{\text{extra}} = q_0 \times 0 = 0 \). No work is required to bring any charge to point E.

---

## 2.8 Potential Energy in an External Field

### 2.8.1 Potential energy of a single charge

This section discusses the potential energy of a charge \( q \) placed in an *external* electric field \( \mathbf{E} \). This external field is produced by sources other than the charge \( q \) itself and is assumed to be unaffected by the presence of \( q \). The field is specified by its potential \( V \).

By definition, the potential energy of a charge \( q \) at a point P in an external potential \( V \) is the work done in bringing the charge from infinity to that point:
$$U = qV(\mathbf{r})$$
where \( V(\mathbf{r}) \) is the external potential at the location of the charge.
```