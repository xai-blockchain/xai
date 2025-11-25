#!/bin/bash
# XAI Blockchain Node Manager
# INTERNAL USE ONLY - DELETE BEFORE PUBLIC RELEASE
# Manage XAI node: start, stop, status, logs

NODE_DIR="$HOME/xai-blockchain"
VENV_PATH="$NODE_DIR/venv/bin/activate"
PID_FILE="$NODE_DIR/node.pid"

cd "$NODE_DIR" || exit 1

case "$1" in
    start)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "Node is already running (PID: $PID)"
                exit 0
            fi
        fi

        echo "Starting XAI node..."
        source "$VENV_PATH"
        nohup python core/node.py > logs/node.log 2>&1 &
        echo $! > "$PID_FILE"
        echo "Node started (PID: $(cat $PID_FILE))"
        ;;

    stop)
        if [ ! -f "$PID_FILE" ]; then
            echo "Node is not running"
            exit 0
        fi

        PID=$(cat "$PID_FILE")
        echo "Stopping XAI node (PID: $PID)..."
        kill "$PID"
        rm "$PID_FILE"
        echo "Node stopped"
        ;;

    restart)
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "Node is running (PID: $PID)"
                exit 0
            else
                echo "Node is not running (stale PID file)"
                rm "$PID_FILE"
                exit 1
            fi
        else
            echo "Node is not running"
            exit 1
        fi
        ;;

    logs)
        tail -f logs/node.log
        ;;

    stats)
        curl -s http://localhost:5000/stats | python -m json.tool
        ;;

    *)
        echo "XAI Blockchain Node Manager"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|stats}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the node"
        echo "  stop     - Stop the node"
        echo "  restart  - Restart the node"
        echo "  status   - Check node status"
        echo "  logs     - View live logs"
        echo "  stats    - Display blockchain stats"
        exit 1
        ;;
esac
