```markdown
# Magnetic Dipoles and Bar Magnets (Extracts from Chapter 5)

## 5.2.2 Bar magnet as an equivalent solenoid

The resemblance of magnetic field lines for a bar magnet and a solenoid suggest that a bar magnet may be thought of as a large number of circulating currents in analogy with a solenoid. Cutting a bar magnet in half is like cutting a solenoid. We get two smaller solenoids with weaker magnetic properties. The field lines remain continuous, emerging from one face of the solenoid and entering into the other face. One can test this analogy by moving a small compass needle in the neighbourhood of a bar magnet and a current-carrying finite solenoid and noting that the deflections of the needle are similar in both cases.

To make this analogy more firm we may calculate the axial field of a finite solenoid depicted in Fig. 5.3 (a). We can demonstrate that at large distances this axial field resembles that of a bar magnet.

The magnitude of the field at point P due to the solenoid is

$$B = \frac{\mu_0}{4\pi} \frac{2m}{r^3} \tag{5.1}$$

This is also the far axial magnetic field of a bar magnet which one may obtain experimentally. Thus, a bar magnet and a solenoid produce similar magnetic fields. The magnetic moment of a bar magnet is thus equal to the magnetic moment of an equivalent solenoid that produces the same magnetic field.

---

## 5.2.3 The dipole in a uniform magnetic field

Let’s place a small compass needle of known magnetic moment \( m \) allowing it to oscillate in the magnetic field. This arrangement is shown in Fig. 5.3(b).

The torque on the needle is [see Eq. (4.23)],

$$\tau = m \times B \tag{5.2}$$

In magnitude \(\tau = mB \sin \theta\)

Here \(\tau\) is restoring torque and \(\theta\) is the angle between \( m \) and \( B \).

An expression for magnetic potential energy can be obtained on lines similar to electrostatic potential energy.

The magnetic potential energy \( U_m \) is given by

$$U_m = \int \tau(\theta) d\theta$$

$$= \int mB \sin \theta \, d\theta = -mB \cos \theta$$

$$= -\mathbf{m} \cdot \mathbf{B} \tag{5.3}$$

We have emphasised in Chapter 2 that the zero of potential energy can be fixed at one’s convenience. Taking the constant of integration to be zero means fixing the zero of potential energy at \(\theta = 90^\circ\), i.e., when the needle is perpendicular to the field. Equation (5.3) shows that potential energy is minimum (\(-mB\)) at \(\theta = 0^\circ\) (most stable position) and maximum (\(+mB\)) at \(\theta = 180^\circ\) (most unstable position).

---

## Example 5.1

(a) What happens if a bar magnet is cut into two pieces: (i) transverse to its length, (ii) along its length?

(b) A magnetised needle in a uniform magnetic field experiences a torque but no net force. An iron nail near a bar magnet, however, experiences a force of attraction in addition to a torque. Why?

(c) Must every magnetic configuration have a north pole and a south pole? What about the field due to a toroid?

(d) Two identical looking iron bars A and B are given, one of which is definitely known to be magnetised. (We do not know which one.) How would one ascertain whether or not both are magnetised? If only one is magnetised, how does one ascertain which one? [Use nothing else but the bars A and B.]

### Solution

(a) In either case, one gets two magnets, each with a north and south pole.

(b) No force if the field is uniform. The iron nail experiences a non-uniform field due to the bar magnet. There is induced magnetic moment in the nail, therefore, it experiences both force and torque. The net force is attractive because the induced south pole (say) in the nail is closer to the north pole of magnet than induced north pole.

(c) Not necessarily. True only if the source of the field has a net non-zero magnetic moment. This is not so for a toroid or even for a straight infinite conductor.

(d) Try to bring different ends of the bars closer. A repulsive force in some situation establishes that both are magnetised. If it is always attractive, then one of them is not magnetised. In a bar magnet the intensity of the magnetic field is the strongest at the two ends (poles) and weakest at the central region. This fact may be used to determine whether A or B is the magnet. In this case, to see which one of the two bars is a magnet, pick up one, (say, A) and lower one of its ends; first on one of the ends of the other (say, B), and then on the middle of B. If you notice that in the middle of B, A experiences no force, then B is magnetised. If you do not notice any change from the end to the middle of B, then A is magnetised.

---

## 5.2.4 The electrostatic analog

Comparison of Eqs. (5.1), (5.2) and (5.3) with the corresponding equations for electric dipole (Chapter 1), suggests that magnetic field at large distances due to a bar magnet of magnetic moment \( m \) can be obtained from the equation for electric field due to an electric dipole of dipole moment \( p \), by making the following replacements:

$$E \rightarrow B, \quad p \rightarrow m, \quad \frac{1}{4\pi\epsilon_0} \rightarrow \frac{\mu_0}{4\pi}$$

In particular, we can write down the equatorial field (\( B_E \)) of a bar magnet at a distance \( r \), for \( r \gg l \), where \( l \) is the size of the magnet:

$$B_E = -\frac{\mu_0 m}{4\pi r^3} \tag{5.4}$$

Likewise, the axial field (\( B_A \)) of a bar magnet for \( r \gg l \) is:

$$B_A = \frac{\mu_0}{4\pi} \frac{2m}{r^3} \tag{5.5}$$

Equation (5.5) is just Eq. (5.1) in the vector form.

**Table 5.1 The dipole analogy**

| Electrostatics | Magnetism |
| :--- | :--- |
| Dipole moment | \(m\) |
| Equatorial Field for a short dipole | \(-\frac{\mu_0 m}{4\pi r^3}\) |
| Axial Field for a short dipole | \(\frac{2\mu_0 m}{4\pi r^3}\) |
| External Field: torque | \(m \times B\) |
| External Field: Energy | \(-m \cdot B\) |

---

## Example 5.2

Figure 5.4 shows a small magnetised needle P placed at a point O. The arrow shows the direction of its magnetic moment. The other arrows show different positions (and orientations of the magnetic moment) of another identical magnetised needle Q.

(a) In which configuration the system is not in equilibrium?
(b) In which configuration is the system in (i) stable, and (ii) unstable equilibrium?
(c) Which configuration corresponds to the lowest potential energy among all the configurations shown?

**FIGURE 5.4**

### Solution

Potential energy of the configuration arises due to the potential energy of one dipole (say, Q) in the magnetic field due to other (P). Use the result that the field due to P is given by the expression [Eqs. (5.4) and (5.5)]:

$$B_P = -\frac{\mu_0 m_P}{4\pi r^3} \quad \text{(on the normal bisector)}$$

$$B_P = \frac{\mu_0 2 m_P}{4\pi r^3} \quad \text{(on the axis)}$$

where \(m_P\) is the magnetic moment of the dipole P. Equilibrium is stable when \(m_Q\) is parallel to \(B_P\), and unstable when it is anti-parallel to \(B_P\).

```