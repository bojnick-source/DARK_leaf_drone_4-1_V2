#include <QApplication>
#include <QMainWindow>

int main(int argc, char** argv) {
    QApplication app(argc, argv);

    QMainWindow window;
    window.setWindowTitle("v2 Studio");
    window.resize(800, 600);
    window.show();

    return app.exec();
}
