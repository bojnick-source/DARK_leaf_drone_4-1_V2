#include <QAbstractItemView>
#include <QApplication>
#include <QCoreApplication>
#include <QDateTime>
#include <QDesktopServices>
#include <QDir>
#include <QFile>
#include <QFormLayout>
#include <QGroupBox>
#include <QHeaderView>
#include <QHBoxLayout>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QMainWindow>
#include <QMessageBox>
#include <QProgressBar>
#include <QPushButton>
#include <QSplitter>
#include <QTableWidget>
#include <QTextEdit>
#include <QUrl>
#include <QVBoxLayout>

#include <optional>

#include "v2/engine/version.hpp"

namespace {

QString findStudioAsset(const QString& relativePath) {
    const QString appDir = QCoreApplication::applicationDirPath();
    const QString cwd = QDir::currentPath();

    const QStringList candidates = {
        QDir(cwd).filePath(relativePath),
        QDir(cwd).filePath("../" + relativePath),
        QDir(cwd).filePath("../../" + relativePath),
        QDir(appDir).filePath(relativePath),
        QDir(appDir).filePath("../" + relativePath),
        QDir(appDir).filePath("../../" + relativePath),
        QDir(appDir).filePath("../../../" + relativePath),
    };

    for (const auto& candidate : candidates) {
        const QString cleaned = QDir::cleanPath(candidate);
        if (QFile::exists(cleaned)) {
            return cleaned;
        }
    }
    return {};
}

std::optional<QJsonObject> loadStudioJson(const QString& filePath, QString* errorOut) {
    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly)) {
        if (errorOut) {
            *errorOut = QString("Unable to open %1").arg(filePath);
        }
        return std::nullopt;
    }

    const QByteArray payload = file.readAll();
    QJsonParseError error;
    QJsonDocument doc = QJsonDocument::fromJson(payload, &error);
    if (error.error != QJsonParseError::NoError || !doc.isObject()) {
        if (errorOut) {
            *errorOut = QString("Invalid JSON in %1: %2").arg(filePath, error.errorString());
        }
        return std::nullopt;
    }

    return doc.object();
}

float clamp01(float value) {
    if (value < 0.0f) {
        return 0.0f;
    }
    if (value > 1.0f) {
        return 1.0f;
    }
    return value;
}

}  // namespace

int main(int argc, char** argv) {
    QApplication app(argc, argv);

    QMainWindow window;
    window.setWindowTitle("v2 Studio • Engineering Console");
    window.resize(1180, 760);

    auto* central = new QWidget();
    auto* rootLayout = new QVBoxLayout(central);
    rootLayout->setContentsMargins(16, 16, 16, 16);
    rootLayout->setSpacing(12);

    auto* headerRow = new QHBoxLayout();
    auto* titleLabel = new QLabel("Studio UI + Engineering Compute");
    titleLabel->setStyleSheet("font-size: 20px; font-weight: 700;");
    headerRow->addWidget(titleLabel);
    headerRow->addStretch();

    const QString engineVersion = QString::fromUtf8(v2::engine::engine_version().data());
    auto* engineLabel = new QLabel(QString("Engine: %1").arg(engineVersion));
    engineLabel->setStyleSheet("color: #4b5563;");
    headerRow->addWidget(engineLabel);
    rootLayout->addLayout(headerRow);

    auto* actionRow = new QHBoxLayout();
    auto* loadSampleButton = new QPushButton("Load Studio Sample");
    auto* runComputeButton = new QPushButton("Run Engineering Snapshot");
    auto* openUiButton = new QPushButton("Open Studio UI (HTML)");
    auto* clearButton = new QPushButton("Clear Logs");
    actionRow->addWidget(loadSampleButton);
    actionRow->addWidget(runComputeButton);
    actionRow->addWidget(openUiButton);
    actionRow->addStretch();
    actionRow->addWidget(clearButton);
    rootLayout->addLayout(actionRow);

    auto* splitter = new QSplitter();

    auto* leftPanel = new QWidget();
    auto* leftLayout = new QVBoxLayout(leftPanel);
    leftLayout->setContentsMargins(0, 0, 0, 0);

    auto* rankedGroup = new QGroupBox("Ranked Topology Candidates");
    auto* rankedLayout = new QVBoxLayout(rankedGroup);
    auto* rankedTable = new QTableWidget(0, 3);
    rankedTable->setHorizontalHeaderLabels({"Name", "Score", "Tag"});
    rankedTable->horizontalHeader()->setStretchLastSection(true);
    rankedTable->verticalHeader()->setVisible(false);
    rankedTable->setEditTriggers(QAbstractItemView::NoEditTriggers);
    rankedTable->setSelectionBehavior(QAbstractItemView::SelectRows);
    rankedLayout->addWidget(rankedTable);
    leftLayout->addWidget(rankedGroup);

    auto* logGroup = new QGroupBox("Studio Log");
    auto* logLayout = new QVBoxLayout(logGroup);
    auto* logView = new QTextEdit();
    logView->setReadOnly(true);
    logView->setMinimumHeight(220);
    logLayout->addWidget(logView);
    leftLayout->addWidget(logGroup);

    splitter->addWidget(leftPanel);

    auto* rightPanel = new QWidget();
    auto* rightLayout = new QVBoxLayout(rightPanel);
    rightLayout->setContentsMargins(0, 0, 0, 0);

    auto* summaryGroup = new QGroupBox("Engineering Summary");
    auto* summaryLayout = new QFormLayout(summaryGroup);
    auto* timestampLabel = new QLabel("—");
    auto* bestLabel = new QLabel("—");
    auto* statusLabel = new QLabel("Idle");
    auto* systemLabel = new QLabel("—");
    auto* flightLabel = new QLabel("—");
    auto* thermalLabel = new QLabel("—");
    auto* windLabel = new QLabel("—");
    auto* salesLabel = new QLabel("—");
    auto* snapshotLabel = new QLabel("—");
    summaryLayout->addRow("Timestamp", timestampLabel);
    summaryLayout->addRow("Best Topology", bestLabel);
    summaryLayout->addRow("AI Status", statusLabel);
    summaryLayout->addRow("System", systemLabel);
    summaryLayout->addRow("Flight", flightLabel);
    summaryLayout->addRow("Thermal", thermalLabel);
    summaryLayout->addRow("Wind", windLabel);
    summaryLayout->addRow("Sales", salesLabel);
    summaryLayout->addRow("Snapshot Score", snapshotLabel);

    auto* confidenceBar = new QProgressBar();
    confidenceBar->setRange(0, 100);
    confidenceBar->setValue(0);
    confidenceBar->setFormat("AI Confidence: %p%");

    rightLayout->addWidget(summaryGroup);
    rightLayout->addWidget(confidenceBar);
    rightLayout->addStretch();

    splitter->addWidget(rightPanel);
    splitter->setStretchFactor(0, 3);
    splitter->setStretchFactor(1, 2);

    rootLayout->addWidget(splitter);
    window.setCentralWidget(central);

    std::optional<QJsonObject> lastPayload;

    auto appendLog = [&](const QString& message) {
        const QString stamp = QDateTime::currentDateTimeUtc().toString("yyyy-MM-dd HH:mm:ss 'UTC'");
        logView->append(QString("[%1] %2").arg(stamp, message));
    };

    auto updateFromPayload = [&](const QJsonObject& root) {
        const QJsonObject ai = root.value("ai").toObject();
        const QJsonObject best = root.value("best").toObject();
        const QJsonObject system = root.value("system").toObject();
        const QJsonObject flight = root.value("flight").toObject();
        const QJsonObject wind = root.value("wind").toObject();
        const QJsonObject sales = root.value("sales").toObject();
        const QJsonObject thermal = root.value("thermal").toObject();

        const QString timestamp = root.value("timestamp_utc").toString("—");
        timestampLabel->setText(timestamp.isEmpty() ? "—" : timestamp);

        const QString bestName = best.value("name").toString("—");
        const double bestScore = best.value("score").toDouble(0.0);
        const QString bestTag = best.value("tag").toString();
        bestLabel->setText(QString("%1 (%2) • %3").arg(bestName).arg(bestScore, 0, 'f', 2).arg(bestTag));

        const QString aiStatus = ai.value("status").toString("Unknown");
        const double aiConfidence = ai.value("confidence").toDouble(0.0);
        statusLabel->setText(QString("%1 (%2)").arg(aiStatus).arg(ai.value("model").toString("model")));
        confidenceBar->setValue(static_cast<int>(aiConfidence * 100.0));

        systemLabel->setText(QString("Rails %1 • Photonics %2 • Thermal nodes %3")
                                 .arg(system.value("power_rails").toInt(0))
                                 .arg(system.value("photonic_links").toInt(0))
                                 .arg(system.value("thermal_nodes").toInt(0)));

        flightLabel->setText(QString("%1 m @ %2 m/s • %3")
                                 .arg(flight.value("target_altitude_m").toDouble(0.0), 0, 'f', 1)
                                 .arg(flight.value("target_speed_m_s").toDouble(0.0), 0, 'f', 1)
                                 .arg(flight.value("mode").toString("mode")));

        double averageTemp = 0.0;
        int thermalCount = 0;
        const QJsonArray nodes = thermal.value("nodes").toArray();
        for (const auto& nodeValue : nodes) {
            const QJsonObject node = nodeValue.toObject();
            averageTemp += node.value("temp").toDouble(0.0);
            ++thermalCount;
        }
        if (thermalCount > 0) {
            averageTemp /= static_cast<double>(thermalCount);
        }
        thermalLabel->setText(QString("Avg %1 °C across %2 nodes")
                                  .arg(averageTemp, 0, 'f', 1)
                                  .arg(thermalCount));

        windLabel->setText(QString("Ship eff. %1 • Kite %2 kW")
                               .arg(wind.value("ship_efficiency").toDouble(0.0), 0, 'f', 2)
                               .arg(wind.value("kite_power_kw").toDouble(0.0), 0, 'f', 1));

        salesLabel->setText(QString("Revenue $%1 • Margin $%2")
                                .arg(sales.value("revenue_usd").toDouble(0.0), 0, 'f', 0)
                                .arg(sales.value("gross_margin_usd").toDouble(0.0), 0, 'f', 0));

        rankedTable->setRowCount(0);
        const QJsonArray ranked = root.value("ranked").toArray();
        rankedTable->setRowCount(ranked.size());
        for (int i = 0; i < ranked.size(); ++i) {
            const QJsonObject entry = ranked.at(i).toObject();
            const QString name = entry.value("name").toString("—");
            const double score = entry.value("score").toDouble(0.0);
            const QString tag = entry.value("tag").toString("—");
            rankedTable->setItem(i, 0, new QTableWidgetItem(name));
            rankedTable->setItem(i, 1, new QTableWidgetItem(QString::number(score, 'f', 2)));
            rankedTable->setItem(i, 2, new QTableWidgetItem(tag));
        }
        rankedTable->resizeColumnsToContents();

        appendLog("Studio payload loaded and UI refreshed.");
    };

    QObject::connect(loadSampleButton, &QPushButton::clicked, [&]() {
        const QString filePath = findStudioAsset("v2/studio/ui/sample_ai_output.json");
        if (filePath.isEmpty()) {
            QMessageBox::warning(&window, "Studio Sample Missing",
                                 "Unable to locate v2/studio/ui/sample_ai_output.json");
            return;
        }
        QString error;
        auto payload = loadStudioJson(filePath, &error);
        if (!payload) {
            QMessageBox::warning(&window, "Invalid Sample", error);
            return;
        }
        lastPayload = *payload;
        updateFromPayload(*payload);
        appendLog(QString("Loaded sample from %1").arg(filePath));
    });

    QObject::connect(runComputeButton, &QPushButton::clicked, [&]() {
        if (!lastPayload) {
            QMessageBox::information(&window, "No Payload", "Load the studio sample first.");
            return;
        }

        const QJsonObject root = *lastPayload;
        const QJsonObject ai = root.value("ai").toObject();
        const QJsonObject best = root.value("best").toObject();
        const QJsonObject thermal = root.value("thermal").toObject();

        double averageTemp = 0.0;
        int thermalCount = 0;
        const QJsonArray nodes = thermal.value("nodes").toArray();
        for (const auto& nodeValue : nodes) {
            averageTemp += nodeValue.toObject().value("temp").toDouble(0.0);
            ++thermalCount;
        }
        if (thermalCount > 0) {
            averageTemp /= static_cast<double>(thermalCount);
        }

        const float bestScore = static_cast<float>(best.value("score").toDouble(0.0));
        const float confidence = static_cast<float>(ai.value("confidence").toDouble(0.0));
        const float thermalPenalty = static_cast<float>(averageTemp / 100.0);
        const float composite = clamp01(0.5f * bestScore + 0.3f * confidence + 0.2f * (1.0f - thermalPenalty));
        snapshotLabel->setText(QString::number(composite, 'f', 2));

        const QString thermalState = averageTemp < 55.0 ? "Cool" : (averageTemp < 70.0 ? "Warm" : "Hot");
        appendLog(QString("Snapshot computed: score %1, thermal %2 (%3 °C avg)")
                      .arg(composite, 0, 'f', 2)
                      .arg(thermalState)
                      .arg(averageTemp, 0, 'f', 1));
    });

    QObject::connect(openUiButton, &QPushButton::clicked, [&]() {
        const QString htmlPath = findStudioAsset("v2/studio/ui/index.html");
        if (htmlPath.isEmpty()) {
            QMessageBox::warning(&window, "Studio UI Missing",
                                 "Unable to locate v2/studio/ui/index.html");
            return;
        }
        QDesktopServices::openUrl(QUrl::fromLocalFile(htmlPath));
        appendLog(QString("Opened Studio UI: %1").arg(htmlPath));
    });

    QObject::connect(clearButton, &QPushButton::clicked, [&]() {
        logView->clear();
        appendLog("Log cleared.");
    });

    appendLog("Studio UI ready. Load the sample to connect UI and compute.");

    window.show();
    return app.exec();
}
