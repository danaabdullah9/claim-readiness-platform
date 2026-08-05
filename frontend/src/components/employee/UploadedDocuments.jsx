import { useEffect, useState } from "react";

function UploadedDocuments({ documents, onPreview }) {
  const [previewDocument, setPreviewDocument] = useState(null);

  useEffect(() => {
    if (!previewDocument) return undefined;
    const handleKeyDown = (event) => {
      if (event.key === "Escape") setPreviewDocument(null);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [previewDocument]);

  function openPreview(document) {
    if (!document.previewUrl) return;
    setPreviewDocument(document);
    onPreview?.(document);
  }

  return (
    <>
      <section className="employee-review-card" aria-labelledby="documents-title">
        <div className="employee-section-heading">
          <div><p className="employee-eyebrow">Claim evidence</p><h2 id="documents-title">Uploaded Documents</h2></div>
          <span className="employee-count-pill">{documents.length} files</span>
        </div>
        <ul className="employee-document-list">
          {documents.map((document) => (
            <li key={document.id || document.name}>
              <span className="employee-document-icon" aria-hidden="true">▤</span>
              <div><strong>{document.name}</strong><small>{document.type} · Uploaded {document.uploadDate}</small></div>
              <span className={`employee-document-status ${document.status === "Verified" ? "is-verified" : "needs-attention"}`}>{document.status}</span>
              <button type="button" disabled={!document.previewUrl} title={!document.previewUrl ? "Original file was not stored for this older claim" : undefined} onClick={() => openPreview(document)}>
                {document.previewUrl ? "Preview" : "Unavailable"}
              </button>
            </li>
          ))}
        </ul>
      </section>

      {previewDocument && (
        <div className="employee-modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setPreviewDocument(null)}>
          <section className="employee-modal employee-document-modal" role="dialog" aria-modal="true" aria-labelledby="employee-preview-title">
            <header><div><p className="employee-eyebrow">Original customer upload</p><h2 id="employee-preview-title">{previewDocument.name}</h2></div><button type="button" className="employee-modal-close" aria-label="Close document preview" onClick={() => setPreviewDocument(null)}>×</button></header>
            <div className="employee-pdf-viewer employee-original-viewer" aria-label={`Original file preview of ${previewDocument.name}`}>
              {/\.(png|jpe?g)$/i.test(previewDocument.name) ? (
                <img src={previewDocument.previewUrl} alt={`${previewDocument.type} uploaded by the customer`} />
              ) : (
                <iframe src={previewDocument.previewUrl} title={`${previewDocument.type} uploaded by the customer`} />
              )}
            </div>
            <footer><span>{previewDocument.status}</span><a href={previewDocument.previewUrl} target="_blank" rel="noreferrer">Open in new tab</a><button type="button" onClick={() => setPreviewDocument(null)}>Close Preview</button></footer>
          </section>
        </div>
      )}
    </>
  );
}

export default UploadedDocuments;
