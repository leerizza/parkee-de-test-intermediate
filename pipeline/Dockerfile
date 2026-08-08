FROM golang:1.21-alpine AS build
WORKDIR /src
COPY go.mod go.sum* ./
RUN go mod download
COPY . .
RUN go build -o /out/pipeline .

FROM alpine:3.19
RUN apk add --no-cache ca-certificates
WORKDIR /app
COPY --from=build /out/pipeline ./pipeline
COPY config ./config
ENTRYPOINT ["./pipeline"]
CMD ["--config", "config/tenants.json", "--state-dir", "/app/state"]
