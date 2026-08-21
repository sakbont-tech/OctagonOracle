from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
import pandas as pd

df = pd.read_csv("data/processed/ml_ufc_data.csv")
y = df["Target"].to_numpy()
df.drop(columns=['Target'], inplace=True, errors='ignore')
X = df.to_numpy()

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

clf = RandomForestClassifier()
clf.fit(X_train_scaled, y_train)
print(clf.score(X_test_scaled, y_test))