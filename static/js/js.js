document.addEventListener('DOMContentLoaded', () => {
  const heroSearchForm = document.getElementById('hero-stock-search-form');
  if (heroSearchForm) {
      heroSearchForm.addEventListener('submit', heroPerformSearch);
  }
});

// Function to show loading modal
function showLoader() {
  document.getElementById('loadingModal').style.display = 'block'; // Show the modal
}

// Function to hide loading modal
function hideLoader() {
  document.getElementById('loadingModal').style.display = 'none'; // Hide the modal
}

function showHeroSuggestions(query) {
  const dropdownContent = document.getElementById('hero-dropdown-content');
  if (query.length < 2) {
      dropdownContent.innerHTML = '';
      return;
  }

  fetch(`/search_stocks?q=${query}`)
      .then(response => response.json())
      .then(data => {
          let resultsHTML = '';
          data.forEach(symbol => {
              resultsHTML += `<div class="suggestion-item" onclick="selectStock('${symbol}')">${symbol}</div>`;
          });
          dropdownContent.innerHTML = resultsHTML;
      })
      .catch(error => console.error('Error fetching suggestions:', error));
}

function selectStock(symbol) {
  document.getElementById('hero-stock-search').value = symbol;
  document.getElementById('hero-dropdown-content').innerHTML = '';
  heroPerformSearch(new Event('submit'));
}

function heroPerformSearch(event) {
  event.preventDefault();
  const query = document.getElementById('hero-stock-search').value.trim().toUpperCase();
  showLoader(); // Show loader when search begins
  fetch(`/stock_details/${query}`)
      .then(response => {
          if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
          return response.json();
      })
      .then(data => {
          hideLoader(); // Hide loader when search completes
          if (data.error || data.length === 0) {
              throw new Error('Stock details not found');
          }
          displayStockDetails(data, 'hero-stock-details');
      })
      .catch(error => {
        console.error('Error:', error);
        hideLoader(); // Hide loader in case of error
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message'; // Apply the error message class
        errorDiv.textContent = 'Error fetching stock details.';
        document.getElementById('hero-stock-details').innerHTML = ''; // Clear any existing content
        document.getElementById('hero-stock-details').appendChild(errorDiv);
        document.getElementById('hero-stock-details').style.display = 'block';
      });
}

function displayStockDetails(data, elementId) {
  const detailsContainer = document.getElementById(elementId);
  const stock = data[0] ? data[0] : {};

  const content = `
      <h3>${stock.Headline || 'N/A'}</h3>
      <p>${stock.Summary || 'N/A'}</p>
      <p><strong>Price Day Before:</strong> ${stock.News_Day_Before || 'N/A'}</p>
      <p><strong>Price Day Of:</strong> ${stock.News_day || 'N/A'}</p>
      <p><strong>Date:</strong> ${stock.Date ? new Date(stock.Date).toLocaleDateString() : 'N/A'}</p>
      <p><strong>Time:</strong> ${stock.Date_Time ? new Date(stock.Date_Time).toLocaleTimeString() : 'N/A'}</p>
      <p><strong>SMA 10:</strong> ${stock.SMA_10 || 'N/A'}</p>
      <p><strong>SMA 20:</strong> ${stock.SMA_20 || 'N/A'}</p>
      <p><strong>SMA 50:</strong> ${stock.SMA_50 || 'N/A'}</p>
      <p><strong>RSI:</strong> ${stock.RSI || 'N/A'} (${stock.RSI_Analysis || 'N/A'})</p>
      <p><strong>MACD:</strong> ${stock.MACD || 'N/A'} (${stock.MACD_Analysis || 'N/A'})</p>
      <p><strong>MACD Signal:</strong> ${stock.MACD_Signal || 'N/A'}</p>
      <p><strong>Sentiment:</strong> ${stock.Sentiment || 'N/A'}</p>
      <p><strong>Adjusted Sentiment:</strong> ${stock.Adjusted_Sentiment || 'N/A'}</p>
  `;

  detailsContainer.innerHTML = content;
  detailsContainer.style.display = 'block';
}


// Function to handle script execution and display data
function runScriptAndDisplayData() {
  showLoader(); // Show loading modal

  fetch('/run-script', { cache: 'no-cache' })
  .then(response => {
      if (!response.ok) {
          throw new Error(`Network response was not ok, status: ${response.status}`);
      }
      return response.json();
  })
  .then(data => {
      console.log(data); // Debugging: Log the data to inspect its structure
      document.getElementById("dataDisplay").innerHTML = "<pre>" + JSON.stringify(data, null, 2) + "</pre>";
      alert("News feed updated successfully.");
  })
  // .catch(error => {
  //   console.error('Error:', error);
  //   document.getElementById("dataDisplay").innerHTML = `Error loading data. Please try again. Details: ${error}`;
  // })
  .finally(() => {
    hideLoader(); // Hide loading modal regardless of success or failure
    document.getElementById("reloadPageBtn").style.display = 'block'; // Show reload page button
  });
}

// Add event listener for the "Run Script" button
document.getElementById("runScriptBtn").addEventListener("click", runScriptAndDisplayData);

// Add event listener for the "Reload Page" button
document.getElementById("reloadPageBtn").addEventListener("click", function() {
  location.reload(); // Reload the page
});


document.querySelector('select[name="news_symbol"]').addEventListener('change', function() {
    this.style.transform = "scale(11)";
    setTimeout(() => {
      this.style.transform = "scale(10)";
    }, 10);
  });

function loadSentimentTrendChart() {
  const chartEl = document.getElementById('sentimentTrendChart');
  if (!chartEl || typeof Chart === 'undefined') {
    return;
  }

  fetch('/api/v1/sentiment_trend')
    .then((response) => response.json())
    .then((rows) => {
      const byDate = {};
      rows.forEach((row) => {
        const date = row.Trend_Date;
        const sentiment = (row.Trend_Sentiment || '').toLowerCase();
        if (!byDate[date]) {
          byDate[date] = { positive: 0, negative: 0, neutral: 0 };
        }
        if (sentiment in byDate[date]) {
          byDate[date][sentiment] = row.count;
        }
      });

      const labels = Object.keys(byDate).sort();
      const positives = labels.map((date) => byDate[date].positive || 0);
      const negatives = labels.map((date) => byDate[date].negative || 0);
      const neutrals = labels.map((date) => byDate[date].neutral || 0);

      if (labels.length === 0) {
        return;
      }

      new Chart(chartEl, {
        type: 'line',
        data: {
          labels,
          datasets: [
            { label: 'Positive', data: positives, borderColor: '#2e7d32', tension: 0.2 },
            { label: 'Negative', data: negatives, borderColor: '#c62828', tension: 0.2 },
            { label: 'Neutral', data: neutrals, borderColor: '#1565c0', tension: 0.2 },
          ],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: 'top' },
          },
        },
      });
    })
    .catch((error) => {
      console.error('Failed to load sentiment trend:', error);
    });
}

document.addEventListener('DOMContentLoaded', loadSentimentTrendChart);

function bindSentimentExplainer() {
  const button = document.getElementById('explainBtn');
  const input = document.getElementById('explainText');
  const output = document.getElementById('explainOutput');
  if (!button || !input || !output) {
    return;
  }

  button.addEventListener('click', () => {
    const text = (input.value || '').trim();
    if (!text) {
      output.textContent = 'Please enter text to explain.';
      return;
    }

    fetch('/api/v1/inference/explain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
      .then((response) => response.json())
      .then((payload) => {
        output.textContent = JSON.stringify(payload, null, 2);
      })
      .catch((error) => {
        output.textContent = `Failed to explain sentiment: ${error}`;
      });
  });
}

document.addEventListener('DOMContentLoaded', bindSentimentExplainer);

function bindReportActions() {
  const downloadBtn = document.getElementById('downloadReportBtn');
  const summaryBtn = document.getElementById('loadSummaryBtn');
  const summaryOutput = document.getElementById('summaryOutput');

  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      window.location.href = '/api/v1/reports/download';
    });
  }

  if (summaryBtn && summaryOutput) {
    summaryBtn.addEventListener('click', () => {
      fetch('/api/v1/reports/sentiment_summary')
        .then((response) => response.json())
        .then((payload) => {
          summaryOutput.textContent = JSON.stringify(payload, null, 2);
        })
        .catch((error) => {
          summaryOutput.textContent = `Failed to load summary: ${error}`;
        });
    });
  }
}

document.addEventListener('DOMContentLoaded', bindReportActions);
