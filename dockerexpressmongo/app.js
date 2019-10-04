const express = require("express");
const logger = require("morgan");
const bodyParser = require("body-parser");
const routes = require("./routes/api/objectsAPI");
const app = express();
const cors = require('cors');

app.use(logger("dev"));
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: false }));

app.use(cors());
app.options('*', cors());


//api
app.use("/", routes);

// catch 404 and forward to error handler
app.use((req, res, next) => {
  var err = new Error("Not Found");
  err.status = 404;
  next(err);
});

// error handlers

// development error handler
// will print stacktrace
if (app.get("env") === "development") {
  app.use((err, req, res, next) => {
    res.status(err.status || 500);
    res.render("error", {
      message: err.message,
      error: err
    });
  });
}

// production error handler
// no stacktraces leaked to user
app.use((err, req, res, next) => {
  res.status(err.status || 500);
  res.render("error", {
    message: err.message,
    error: {}
  });
});

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => console.log(`Server started on port ${PORT}`));
