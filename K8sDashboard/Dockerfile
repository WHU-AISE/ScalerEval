FROM node:14

WORKDIR /app

COPY package*.json ./

RUN git config --global url.https://github.com/.insteadOf git://github.com/

RUN npm install --legacy-peer-deps

COPY . .

EXPOSE 10000

CMD ["npm", "run", "serve", "--", "--port", "10000"]