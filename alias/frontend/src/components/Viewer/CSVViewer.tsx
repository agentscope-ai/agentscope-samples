import React from "react";
import { BaseViewerProps } from "./types";

export const CSVViewer: React.FC<BaseViewerProps> = ({ content, style }) => {
  const parseCSV = (csvContent: string) => {
    try {
      // Normalize line breaks
      const normalizedContent = csvContent
        .replace(/\r\n/g, "\n")
        .replace(/\r/g, "\n");
      const rows = normalizedContent.split("\n").filter((row) => row.trim());

      if (rows.length === 0) {
        throw new Error("Empty CSV content");
      }

      // Simple CSV parsing
      const parseRow = (row: string) => {
        try {
          let cells = [];
          let cell = "";
          let inQuotes = false;

          for (let i = 0; i < row.length; i++) {
            const char = row[i];
            if (char === '"') {
              inQuotes = !inQuotes;
            } else if (char === "," && !inQuotes) {
              cells.push(cell);
              cell = "";
            } else {
              cell += char;
            }
          }
          cells.push(cell);
          return cells.map((c) => c.trim().replace(/^"|"$/g, ""));
        } catch (error) {
          console.error("Error parsing CSV row:", error);
          throw new Error(`Failed to parse row: ${row}`);
        }
      };

      const headers = parseRow(rows[0]);
      if (headers.length === 0) {
        throw new Error("No headers found in CSV");
      }

      const data = rows.slice(1).map((row, index) => {
        try {
          const parsedRow = parseRow(row);
          // Ensure each row has the same number of columns as header
          if (parsedRow.length !== headers.length) {
            console.warn(
              `Row ${index + 1} has ${parsedRow.length} columns, expected ${
                headers.length
              }`,
            );
            // Pad or truncate columns
            return parsedRow.length > headers.length
              ? parsedRow.slice(0, headers.length)
              : [
                  ...parsedRow,
                  ...Array(headers.length - parsedRow.length).fill(""),
                ];
          }
          return parsedRow;
        } catch (error) {
          console.error(`Error parsing row ${index + 1}:`, error);
          // Return empty row instead of interrupting entire parsing
          return Array(headers.length).fill("");
        }
      });

      return { headers, data };
    } catch (error) {
      console.error("Error parsing CSV:", error);
      return {
        headers: [],
        data: [],
        error: error instanceof Error ? error.message : "Failed to parse CSV",
      };
    }
  };

  try {
    const { headers, data, error } = parseCSV(content);

    // Show error message if parsing fails
    if (error) {
      return (
        <div
          style={{
            padding: "16px",
            color: "#ff4d4f",
            backgroundColor: "#fff2f0",
            border: "1px solid #ffccc7",
            borderRadius: "4px",
          }}
        >
          Error: {error}
        </div>
      );
    }

    // Show prompt message if there is no data
    if (headers.length === 0 || data.length === 0) {
      return (
        <div
          style={{
            padding: "16px",
            color: "#666",
            backgroundColor: "#fafafa",
            border: "1px solid #f0f0f0",
            borderRadius: "4px",
          }}
        >
          No valid CSV data found
        </div>
      );
    }

    return (
      <div
        style={{
          ...style,
          overflow: "auto",
          // maxHeight: '500px'
        }}
      >
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "14px",
          }}
        >
          <thead>
            <tr>
              {headers.map((header, index) => (
                <th
                  key={index}
                  style={{
                    padding: "8px",
                    backgroundColor: "#fafafa",
                    borderBottom: "1px solid #f0f0f0",
                    position: "sticky",
                    top: 0,
                    textAlign: "left",
                  }}
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <td
                    key={cellIndex}
                    style={{
                      padding: "8px",
                      borderBottom: "1px solid #f0f0f0",
                    }}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  } catch (error) {
    // Component-level error handling
    console.error("Component error:", error);
    return (
      <div
        style={{
          padding: "16px",
          color: "#ff4d4f",
          backgroundColor: "#fff2f0",
          border: "1px solid #ffccc7",
          borderRadius: "4px",
        }}
      >
        An unexpected error occurred while rendering the CSV viewer
      </div>
    );
  }
};
