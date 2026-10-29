/** 3x3 confusion matrix: rows are the hand labels, columns the predicted labels. Correct cells are highlighted. */
export default function ConfusionMatrix({ title, matrix, labels }) {
  const max = Math.max(1, ...matrix.flat());
  return (
    <table className="confusion">
      <caption>{title}</caption>
      <thead>
        <tr>
          <th scope="col">
            <span className="visually-hidden">Hand label</span>
          </th>
          {labels.map((label) => (
            <th key={label} scope="col">
              Predicted {label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {matrix.map((row, i) => (
          <tr key={labels[i]}>
            <th scope="row">Labelled {labels[i]}</th>
            {row.map((count, j) => (
              <td
                key={labels[j]}
                className={i === j ? 'confusion__cell confusion__cell--correct' : 'confusion__cell'}
                style={{ '--strength': count / max }}
              >
                {count}
                {i === j && <span className="visually-hidden"> (correct)</span>}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
