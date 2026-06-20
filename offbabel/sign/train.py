"""Train a KNN classifier on captured BSL landmarks; report holdout accuracy + confusion.

Run:  python -m offbabel.sign.train

KNN = zero training time, instant iteration (the de-risk). Swap to a tiny MLP after the
gate only if you want smoother confidence. We print a confusion matrix AND explicitly flag
the BSL vowel pairs (E/O etc.) — those are the ones that quietly tank a HELLO demo.
"""
import numpy as np
import pandas as pd
import joblib
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

from .. import config

# BSL vowels share the "touch a passive fingertip" shape -> the subtlest discrimination.
VOWEL_PAIRS = [("E", "O"), ("E", "I"), ("O", "U"), ("A", "E"), ("I", "U")]


def main():
    df = pd.read_csv(config.LANDMARKS_CSV)
    if len(df) < 20:
        print(f"Only {len(df)} samples — capture more (aim 30-50/letter) before trusting this.")
    X = df.drop(columns=["label"]).values.astype(np.float32)
    y = df["label"].astype(str).values
    labels = sorted(set(y))

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=0)
    clf = KNeighborsClassifier(n_neighbors=5, weights="distance")
    clf.fit(Xtr, ytr)
    pred = clf.predict(Xte)

    print("\n=== Held-out report ===")
    print(classification_report(yte, pred, zero_division=0))

    cm = confusion_matrix(yte, pred, labels=labels)
    print("Labels:", labels)
    print("Confusion matrix (rows=true, cols=pred):")
    print(cm)

    print("\n=== Vowel-trap check (PRD: E/O are the demo killers) ===")
    idx = {lab: i for i, lab in enumerate(labels)}
    for a, b in VOWEL_PAIRS:
        if a in idx and b in idx:
            ab = cm[idx[a]][idx[b]]
            ba = cm[idx[b]][idx[a]]
            flag = "  <-- WATCH" if (ab + ba) > 0 else "  ok"
            print(f"  {a}<->{b}: {a}->{b}={ab}, {b}->{a}={ba}{flag}")

    joblib.dump({"model": clf, "labels": labels}, config.SIGN_MODEL_PATH)
    print(f"\nSaved model -> {config.SIGN_MODEL_PATH}")


if __name__ == "__main__":
    main()
